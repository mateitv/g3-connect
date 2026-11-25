#!/usr/bin/env python3
"""Static disassembly triage for the F3/F3 Pro RAW4TFT BLE image."""
from __future__ import annotations
import argparse
import hashlib
import struct
from collections import deque
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS, CS_MODE_LITTLE_ENDIAN
from capstone.arm_const import ARM_OP_IMM, ARM_OP_MEM, ARM_REG_PC

def disassembler(mode):
    md = Cs(CS_ARCH_ARM, mode)
    md.detail = True
    md.skipdata = True
    return md

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--base", type=lambda x: int(x, 0), default=0x0C000400)
    ap.add_argument("--out", type=Path, default=Path("f3-ble-disassembly.md"))
    ap.add_argument("--vectors", type=lambda x: int(x, 0), default=0x400)
    ap.add_argument("--max-functions", type=int, default=300)
    args = ap.parse_args()
    data = args.image.read_bytes()
    if data[:7] != b"RAW4TFT":
        raise SystemExit(f"Unexpected image magic: {data[:16]!r}")
    initial_sp, reset = struct.unpack_from("<II", data, args.vectors)
    reset_addr = reset & ~1
    reset_off = reset_addr - args.base
    if not (0 <= reset_off < len(data)):
        raise SystemExit(f"Reset vector {reset:#x} does not map into image using base {args.base:#x}")

    vector_entries = []
    seen_vectors = set()
    for index in range(1, min(256, (len(data) - args.vectors) // 4)):
        value = struct.unpack_from("<I", data, args.vectors + index * 4)[0]
        addr = value & ~1
        off = addr - args.base
        if value & 1 and 0 <= off < len(data) and addr not in seen_vectors:
            seen_vectors.add(addr)
            vector_entries.append((index, value, off))

    modes = [
        ("Thumb M-class", CS_MODE_THUMB | CS_MODE_MCLASS | CS_MODE_LITTLE_ENDIAN),
        ("Thumb generic", CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN),
    ]
    chosen = None
    reset_ins = []
    mode_results = []
    for name, mode in modes:
        md = disassembler(mode)
        ins = list(md.disasm(data[reset_off:reset_off + 0x100], reset_addr))
        valid = [x for x in ins if x.mnemonic != ".byte"]
        mode_results.append((name, len(valid)))
        if chosen is None or len(valid) > len(reset_ins):
            chosen, reset_ins = md, valid
    mode_name = max(mode_results, key=lambda x: x[1])[0]
    if not reset_ins:
        raise SystemExit("Capstone could not decode the reset vector in either Thumb mode")

    # Start from reset plus every distinct in-image interrupt vector, then walk
    # direct BL targets. This is static triage; it does not execute the image.
    queue = deque([reset_addr] + [value & ~1 for _, value, _ in vector_entries])
    seen = set()
    functions = []
    literal_refs = set()
    while queue and len(functions) < args.max_functions:
        addr = queue.popleft() & ~1
        off = addr - args.base
        if addr in seen or not (0 <= off < len(data)):
            continue
        seen.add(addr)
        insns = list(chosen.disasm(data[off:off + 0x240], addr))
        valid = [x for x in insns if x.mnemonic != ".byte"]
        if not valid:
            continue
        functions.append((addr, off, valid))
        for ins in valid:
            if ins.mnemonic.startswith("bl"):
                for op in ins.operands:
                    if op.type == ARM_OP_IMM:
                        target = op.imm & ~1
                        if args.base <= target < args.base + len(data) and target not in seen:
                            queue.append(target)
            if ins.mnemonic.startswith("ldr") and len(ins.operands) >= 2:
                op = ins.operands[1]
                if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC:
                    literal_addr = ((ins.address + 4) & ~3) + op.mem.disp
                    literal_off = literal_addr - args.base
                    if 0 <= literal_off <= len(data) - 4:
                        value = struct.unpack_from("<I", data, literal_off)[0]
                        if 0x40000000 <= value <= 0x6FFFFFFF or 0xE0000000 <= value <= 0xFFFFFFFF:
                            literal_refs.add((value, addr, ins.address))

    lines = [
        "# F3/F3 Pro BLE firmware disassembly triage",
        "",
        "> Static, offline analysis of a decrypted stock image. No scooter I/O or firmware writes.",
        "",
        f"- Image size: {len(data):,} bytes",
        f"- SHA-256: {hashlib.sha256(data).hexdigest()}",
        f"- Image magic: {data[:7]!r}",
        f"- Header word at 0x0C: 0x{struct.unpack_from('<I', data, 0x0C)[0]:08X}",
        f"- Header load/vector offset field: 0x{struct.unpack_from('<I', data, 0x18)[0]:X}",
        f"- Vector-table file offset: 0x{args.vectors:X}",
        f"- Initial stack pointer: 0x{initial_sp:08X}",
        f"- Reset vector: 0x{reset:08X} (Thumb entry 0x{reset_addr:08X})",
        f"- Derived file-to-address base: 0x{args.base:08X}",
        f"- Reset handler file offset: 0x{reset_off:X}",
        f"- Decoder selected: {mode_name}",
        f"- Reset-handler instructions decoded: {max(x[1] for x in mode_results)}",
        "",
        "## Decoder comparison",
        "",
    ]
    for name, count in mode_results:
        lines.append(f"- {name}: {count} non-data instructions in first 0x100 bytes")
    lines.extend(["", "## Vector table targets", "", f"- Unique in-image Thumb targets: {len(vector_entries)}"])
    for index, value, off in vector_entries:
        lines.append(f"- Vector {index}: 0x{value:08X} -> file offset 0x{off:X}")
    lines.extend(["", "## Reset handler (first 0x300 bytes)", ""])
    for ins in chosen.disasm(data[reset_off:reset_off + 0x300], reset_addr):
        lines.append(f"0x{ins.address:08X}: {ins.mnemonic:8} {ins.op_str}")
    lines.extend(["", "## Vector handler entry samples", ""])
    for index, value, off in vector_entries[:24]:
        addr = value & ~1
        lines.extend(["", f"### Vector {index}: 0x{value:08X} (file offset 0x{off:X})"])
        for ins in chosen.disasm(data[off:off + 0x70], addr):
            lines.append(f"0x{ins.address:08X}: {ins.mnemonic:8} {ins.op_str}")
    lines.extend(["", "## Direct-call graph seeded from reset and vector handlers", ""])
    lines.append(f"- Reachable function candidates decoded: {len(functions)}")
    for addr, off, insns in functions[:80]:
        lines.extend(["", f"### Function candidate 0x{addr:08X} (file offset 0x{off:X})"])
        for ins in insns[:32]:
            lines.append(f"0x{ins.address:08X}: {ins.mnemonic:8} {ins.op_str}")
    lines.extend(["", "## Memory-mapped address references via PC-relative literal loads", ""])
    if literal_refs:
        for value, fn, insaddr in sorted(literal_refs):
            lines.append(f"- 0x{value:08X} (referenced at 0x{insaddr:08X}, function candidate 0x{fn:08X})")
    else:
        lines.append("- No matching peripheral constants found in sampled reset/vector call graph.")
    lines.extend([
        "",
        "## Caveats",
        "- The file-to-address base is inferred from the header/vector layout and checked against in-image Thumb targets.",
        "- Direct-call traversal is heuristic; indirect calls, jump tables, RTOS tasks, and callbacks are not fully recovered.",
        "- Vector names and peripheral labels are not available in this raw image.",
        "- Disassembly is not a validated source reconstruction. Do not patch or transmit experimental commands based on it.",
    ])
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.out.read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
