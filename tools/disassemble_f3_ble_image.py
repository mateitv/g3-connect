#!/usr/bin/env python3
"""Disassemble the F3/F3 Pro RAW4TFT BLE image using Capstone (offline only)."""
from __future__ import annotations
import argparse
import hashlib
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS, CS_MODE_LITTLE_ENDIAN

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--base", type=lambda x: int(x, 0), default=0x0C000000)
    ap.add_argument("--out", type=Path, default=Path("f3-ble-disassembly.md"))
    ap.add_argument("--vectors", type=lambda x: int(x, 0), default=0x400)
    args = ap.parse_args()
    data = args.image.read_bytes()
    if data[:7] != b"RAW4TFT":
        raise SystemExit(f"Unexpected image magic: {data[:16]!r}")
    if args.vectors + 8 > len(data):
        raise SystemExit("Vector-table offset outside image")
    initial_sp, reset = struct.unpack_from("<II", data, args.vectors)
    reset_addr = reset & ~1
    reset_off = reset_addr - args.base
    if not (0 <= reset_off < len(data)):
        raise SystemExit(f"Reset vector {reset:#x} does not map into image using base {args.base:#x}")
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS | CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    lines = [
        "# F3/F3 Pro BLE firmware disassembly triage",
        "",
        "> Static, offline analysis of a decrypted stock image. No scooter I/O or firmware writes.",
        "",
        f"- Image size: {len(data):,} bytes",
        f"- SHA-256: {hashlib.sha256(data).hexdigest()}",
        f"- Image magic: {data[:7]!r}",
        f"- Header word at 0x0C: 0x{struct.unpack_from('<I', data, 0x0C)[0]:08X}",
        f"- Vector-table offset: 0x{args.vectors:X}",
        f"- Initial stack pointer: 0x{initial_sp:08X}",
        f"- Reset vector: 0x{reset:08X} (Thumb entry 0x{reset_addr:08X})",
        f"- Derived memory mapping base: 0x{args.base:08X}",
        f"- Reset handler file offset: 0x{reset_off:X}",
        "",
        "## Reset handler",
        "",
    ]
    for ins in md.disasm(data[reset_off:reset_off + 0x300], reset_addr):
        lines.append(f"0x{ins.address:08X}: {ins.mnemonic:8} {ins.op_str}")
    lines.extend(["", "## Vector table handlers", ""])
    unique = []
    seen = set()
    for i in range(1, min(256, (len(data) - args.vectors) // 4)):
        value = struct.unpack_from("<I", data, args.vectors + i * 4)[0]
        addr = value & ~1
        off = addr - args.base
        if value & 1 and 0 <= off < len(data) and addr not in seen:
            seen.add(addr)
            unique.append((i, value, off))
    lines.append(f"- Unique in-image Thumb vector targets: {len(unique)}")
    for index, value, off in unique[:48]:
        lines.extend(["", f"### Vector {index}: 0x{value:08X} (file offset 0x{off:X})", ""])
        for ins in md.disasm(data[off:off + 0x60], value & ~1):
            lines.append(f"0x{ins.address:08X}: {ins.mnemonic:8} {ins.op_str}")
    lines.extend(["", "## Memory-mapped address references in entry/vector code", ""])
    refs = set()
    for _, value, off in [(0, reset, reset_off)] + unique[:48]:
        addr = value & ~1
        for ins in md.disasm(data[off:off + 0x180], addr):
            if ins.mnemonic.startswith(("ldr", "mov", "add")):
                for op in getattr(ins, "operands", []):
                    if op.type == 2 and 0x40000000 <= op.imm <= 0xFFFFFFFF:
                        refs.add(op.imm)
    lines.extend(f"- 0x{x:08X}" for x in sorted(refs)[:100])
    lines.extend([
        "",
        "## Caveats",
        "- The image base is inferred by mapping the reset-vector address to the observed file offset; confirm against additional vector entries and hardware documentation.",
        "- Vector names are not available in this raw image. The output lists vector indices only.",
        "- Disassembly is heuristic until the MCU core and memory map are independently confirmed.",
        "- Do not patch or transmit experimental commands based on these findings.",
    ])
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.out.read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
