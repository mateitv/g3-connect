#!/usr/bin/env python3
"""Whole-image Thumb xref sweep for key F3 BLE display/media strings.

This is a heuristic offline scan. It does not execute, patch, or transmit firmware.
"""
from __future__ import annotations
import argparse
import re
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS, CS_MODE_LITTLE_ENDIAN
from capstone.arm_const import ARM_OP_IMM, ARM_OP_MEM, ARM_REG_PC

KEYWORDS = (
    b"update_display_content", b"write_cb tft", b"Display initialized",
    b"st7735", b"/dev/spi0", b"/dev/gpio", b"lvgl_view",
    b"lv_draw_label", b"bts_media_enable", b"ninebot_gatt_server",
    b"Uart dispatcher", b"ctrl_screen_backlight", b"is_tft_start",
    b"tft_upgrade_status",
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--base", type=lambda x: int(x, 0), default=0x0C000000)
    ap.add_argument("--out", type=Path, default=Path("f3-ble-string-xrefs.md"))
    args = ap.parse_args()
    data = args.image.read_bytes()
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS | CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    md.skipdata = False

    strings = {}
    for m in re.finditer(rb"[\x20-\x7e]{4,}", data):
        raw = m.group()
        if any(k.lower() in raw.lower() for k in KEYWORDS):
            strings[args.base + m.start()] = (m.start(), raw.decode("ascii", "replace"))

    def string_at(address):
        if address in strings:
            return strings[address]
        return None

    movw = {}
    refs = set()
    decoded = 0
    for off in range(0x400, len(data) - 4, 2):
        address = args.base + off
        ins_list = list(md.disasm(data[off:off + 4], address, count=1))
        if not ins_list:
            continue
        ins = ins_list[0]
        decoded += 1
        if ins.mnemonic == "movw" and len(ins.operands) >= 2:
            movw[(ins.operands[0].reg, off)] = ins.operands[1].imm & 0xFFFF
        elif ins.mnemonic == "movt" and len(ins.operands) >= 2:
            reg = ins.operands[0].reg
            hi = ins.operands[1].imm & 0xFFFF
            for (lowreg, lowoff), low in list(movw.items()):
                if lowreg == reg and 0 < off - lowoff <= 0x20:
                    found = string_at((hi << 16) | low)
                    if found:
                        refs.add((found[0], found[1], lowoff, off, "MOVW/MOVT"))
                    del movw[(lowreg, lowoff)]
        if ins.mnemonic == "adr" and len(ins.operands) >= 2 and ins.operands[1].type == ARM_OP_IMM:
            target = ((address + 4) & ~3) + ins.operands[1].imm
            found = string_at(target)
            if found:
                refs.add((found[0], found[1], off, off, "ADR"))
        if ins.mnemonic.startswith("ldr") and len(ins.operands) >= 2:
            op = ins.operands[1]
            if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC:
                literal_addr = ((address + 4) & ~3) + op.mem.disp
                literal_off = literal_addr - args.base
                if 0 <= literal_off <= len(data) - 4:
                    value = struct.unpack_from("<I", data, literal_off)[0]
                    found = string_at(value)
                    if found:
                        refs.add((found[0], found[1], literal_off, off, "LDR literal"))

    lines = [
        "# F3/F3 Pro BLE display/media string xref sweep",
        "",
        "> Whole-image Thumb instruction scan; heuristic only, no firmware execution or modification.",
        "",
        f"- Image bytes: {len(data):,}",
        f"- Candidate display/media strings: {len(strings)}",
        f"- Halfword offsets decoded as instructions: {decoded:,}",
        f"- String references resolved: {len(refs)}",
        "",
    ]
    if refs:
        for target_off, text, source_off, ins_off, kind in sorted(refs):
            lines.append(f"- {kind}: string file offset 0x{target_off:X} ({text[:160]!r}); source/literal offsets 0x{source_off:X} / 0x{ins_off:X}")
    else:
        lines.append("No direct ADR, MOVW/MOVT, or PC-relative LDR string references resolved.")
    lines.extend(["", "## Candidate strings", ""])
    for address, (off, text) in sorted(strings.items()):
        lines.append(f"- file offset 0x{off:X}: {text[:180]!r}")
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.out.read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
