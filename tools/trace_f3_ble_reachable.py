#!/usr/bin/env python3
"""Reachability-guided Thumb CFG and string-reference triage for F3 BLE firmware."""
from __future__ import annotations
import argparse, hashlib, re, struct
from collections import deque
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS, CS_MODE_LITTLE_ENDIAN, CS_GRP_JUMP
from capstone.arm_const import ARM_OP_IMM, ARM_OP_MEM, ARM_REG_PC

KEYWORDS = (
    b"bts_media_enable", b"bts_media_next_song", b"bts_media_previous_song",
    b"bts_media_status_change_notify", b"bts_avrcp_controller_nextsong",
    b"bts_avrcp_controller_presong", b"btapp_navi_data_received",
    b"ninebot_gatt_server", b"lvgl_view", b"lv_draw_label",
    b"update_display_content", b"write_cb tft", b"Uart dispatcher",
    b"uart_process_task", b"Display initialized", b"st7735",
    b"/dev/spi0", b"/dev/gpio", b"navi_task", b"bts_task",
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--base", type=lambda x: int(x, 0), default=0x0C000000)
    ap.add_argument("--vectors", type=lambda x: int(x, 0), default=0x400)
    ap.add_argument("--max-functions", type=int, default=2000)
    ap.add_argument("--max-instructions-per-function", type=int, default=12000)
    ap.add_argument("--out", type=Path, default=Path("f3-ble-reachable-trace.md"))
    args = ap.parse_args()
    data = args.image.read_bytes()
    if data[:7] != b"RAW4TFT":
        raise SystemExit("Input does not have RAW4TFT image magic")
    if args.vectors + 8 > len(data):
        raise SystemExit("Vector-table offset is outside the image")

    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS | CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    strings = []
    for m in re.finditer(rb"[\x20-\x7e]{4,}", data):
        raw = m.group()
        if any(k.lower() in raw.lower() for k in KEYWORDS):
            strings.append((args.base + m.start(), args.base + m.start() + len(raw),
                            m.start(), raw.decode("ascii", "replace")))
    strings.sort()

    def string_at(value):
        for candidate in (value, args.base + value, args.base + 0x400 + value):
            lo, hi = 0, len(strings)
            while lo < hi:
                mid = (lo + hi) // 2
                if strings[mid][0] <= candidate: lo = mid + 1
                else: hi = mid
            if lo:
                start, end, file_off, label = strings[lo - 1]
                if start <= candidate < end:
                    delta = candidate - start
                    return file_off + delta, label[delta:]
        return None

    initial_sp, reset = struct.unpack_from("<II", data, args.vectors)
    vectors = []
    for index in range(1, min(256, (len(data) - args.vectors) // 4)):
        value = struct.unpack_from("<I", data, args.vectors + index * 4)[0]
        target = value & ~1
        if value & 1 and args.base <= target < args.base + len(data):
            vectors.append((index, value, target))

    pending = deque([("reset", reset & ~1)] + [(f"vector_{i}", t) for i, _, t in vectors])
    queued = {t for _, t in pending}
    functions, refs, calls = [], set(), set()
    total_ins = 0

    def add_function(target, origin):
        target &= ~1
        if args.base <= target < args.base + len(data) and target not in queued:
            queued.add(target)
            pending.append((origin, target))

    while pending and len(functions) < args.max_functions:
        origin, start = pending.popleft()
        off0 = start - args.base
        if not (0 <= off0 < len(data)): continue
        blocks, seen_blocks, seen_ins = deque([start]), set(), set()
        fn_calls, fn_refs = set(), set()
        count = 0
        while blocks and count < args.max_instructions_per_function:
            pc = blocks.popleft() & ~1
            movw_values = {}
            if pc in seen_blocks: continue
            seen_blocks.add(pc)
            while args.base <= pc < args.base + len(data) and count < args.max_instructions_per_function:
                if pc in seen_ins: break
                off = pc - args.base
                decoded = list(md.disasm(data[off:min(len(data), off + 4)], pc, count=1))
                if not decoded: break
                ins = decoded[0]
                seen_ins.add(pc); count += 1; total_ins += 1
                next_pc = pc + ins.size

                if ins.mnemonic == "movw" and len(ins.operands) >= 2:
                    movw_values[ins.operands[0].reg] = ins.operands[1].imm & 0xffff
                if ins.mnemonic == "movt" and len(ins.operands) >= 2:
                    reg = ins.operands[0].reg
                    if reg in movw_values:
                        value = ((ins.operands[1].imm & 0xffff) << 16) | movw_values[reg]
                        found = string_at(value)
                        if found: fn_refs.add((found[0], found[1], pc, "MOVW/MOVT"))
                        del movw_values[reg]
                if ins.mnemonic == "adr" and len(ins.operands) >= 2 and ins.operands[1].type == ARM_OP_IMM:
                    raw = ins.operands[1].imm
                    for candidate in (raw, ((pc + 4) & ~3) + raw):
                        found = string_at(candidate)
                        if found:
                            fn_refs.add((found[0], found[1], pc, "ADR")); break
                if ins.mnemonic.startswith("ldr") and len(ins.operands) >= 2:
                    mem = ins.operands[1]
                    if mem.type == ARM_OP_MEM and mem.mem.base == ARM_REG_PC:
                        literal = ((pc + 4) & ~3) + mem.mem.disp
                        literal_off = literal - args.base
                        if 0 <= literal_off <= len(data) - 4:
                            value = struct.unpack_from("<I", data, literal_off)[0]
                            found = string_at(value)
                            if found: fn_refs.add((found[0], found[1], pc, "LDR literal"))

                if ins.mnemonic.startswith("bl") and ins.operands and ins.operands[0].type == ARM_OP_IMM:
                    target = ins.operands[0].imm & ~1
                    fn_calls.add((target, pc)); calls.add((start, pc, target))
                    add_function(target, f"called_from_{start:08X}")
                    pc = next_pc
                    continue

                if ins.mnemonic == "bx" and ins.op_str.strip() == "lr": break
                if ins.mnemonic.startswith("pop") and "pc" in ins.op_str: break
                if ins.mnemonic in ("mov", "movs") and ins.op_str.replace(" ", "") == "pc,lr": break

                if ins.group(CS_GRP_JUMP) or ins.mnemonic in ("cbz", "cbnz"):
                    target = None
                    if ins.operands and ins.operands[-1].type == ARM_OP_IMM:
                        target = ins.operands[-1].imm & ~1
                    if target is not None and args.base <= target < args.base + len(data):
                        blocks.append(target)
                    if ins.mnemonic in ("b", "b.w"): break
                    pc = next_pc
                    continue
                if ins.mnemonic in ("bx", "blx", "tbb", "tbh"): break
                pc = next_pc

        functions.append((start, origin, count, len(seen_blocks), sorted(fn_calls), sorted(fn_refs)))
        for file_off, label, ins_addr, kind in fn_refs:
            refs.add((file_off, label, start, ins_addr, kind))

    lines = [
        "# F3/F3 Pro BLE reachability-guided Thumb trace", "",
        "> Offline static analysis only. CFG recovery is heuristic; no scooter I/O or firmware writes.", "",
        f"- Image size: {len(data):,} bytes",
        f"- SHA-256: {hashlib.sha256(data).hexdigest()}",
        f"- Vector offset: 0x{args.vectors:X}",
        f"- Initial stack pointer: 0x{initial_sp:08X}",
        f"- Reset vector: 0x{reset:08X}",
        f"- Valid vector seeds: {len(vectors)}",
        f"- Function candidates visited: {len(functions)}",
        f"- Decoded reachable instructions: {total_ins:,}",
        f"- Direct calls discovered: {len(calls)}",
        f"- Candidate string references: {len(refs)}", "",
        "## Reachable references to media/display/UART strings", ""
    ]
    if refs:
        for file_off, label, fn, ins_addr, kind in sorted(refs):
            lines.append(f"- {kind}: file+0x{file_off:X} {label[:160]!r} from function 0x{fn:08X} at 0x{ins_addr:08X}")
    else: lines.append("- No candidate references resolved from reachable code.")
    lines.extend(["", "## Functions with candidate string references", ""])
    ref_fns = {fn for _, _, fn, _, _ in refs}
    for start, origin, count, nblocks, fn_calls, fn_refs in functions:
        if start in ref_fns:
            lines.append(f"- 0x{start:08X} ({origin}): {count} instructions, {nblocks} blocks")
            for target, call_addr in fn_calls: lines.append(f"  - calls 0x{target:08X} at 0x{call_addr:08X}")
    lines.extend(["", "## Function candidate summary", ""])
    for start, origin, count, nblocks, fn_calls, fn_refs in functions:
        if fn_calls or fn_refs:
            lines.append(f"- 0x{start:08X} ({origin}): {count} instructions, {nblocks} blocks, {len(fn_calls)} calls, {len(fn_refs)} refs")
    lines.extend(["", "## Limitations",
        "- Vector-table and image mapping are inferred from RAW4TFT layout and need independent validation.",
        "- Indirect calls, RTOS-created tasks, callbacks, and computed jump tables may be missed.",
        "- Mixed code/data and literal pools can still create false positives.",
        "- Do not patch or transmit experimental commands based on this report."])
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.out.read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
