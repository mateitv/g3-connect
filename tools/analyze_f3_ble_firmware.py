#!/usr/bin/env python3
"""Offline static triage for a stock Ninebot X3 F3/F3 Pro BLE firmware package.

This tool NEVER connects to a scooter and NEVER modifies or flashes firmware.
It reports archive members, hashes, likely image headers, Cortex-M vector-table
candidates, entropy windows, and printable strings to guide later disassembly.
"""
from __future__ import annotations
import argparse
import hashlib
import math
import re
import struct
import zipfile
from collections import Counter
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def strings(data: bytes, min_len: int = 5):
    pat = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    return [m.group().decode("ascii", "replace") for m in pat.finditer(data)]


def vector_candidates(data: bytes):
    found = []
    # Common Cortex-M flash bases. These are hypotheses, not a chip identification.
    bases = (0x08000000, 0x08001000, 0x00000000, 0x10000000)
    for off in range(0, min(len(data) - 8, 0x4000), 4):
        sp, reset = struct.unpack_from("<II", data, off)
        if 0x20000000 <= sp <= 0x20080000 and (reset & 1):
            for base in bases:
                pc = reset & ~1
                if base <= pc < base + len(data) + 0x20000:
                    found.append((off, sp, reset, base))
                    break
    return found[:30]


def analyse_blob(name: str, data: bytes):
    lines = [
        f"### {name}",
        f"- Size: {len(data):,} bytes",
        f"- SHA-256: {sha256(data)}",
        f"- First 32 bytes: {data[:32].hex(' ')}",
        f"- Whole-file entropy: {entropy(data):.4f} bits/byte",
    ]
    signatures = {
        "ZIP": b"PK\x03\x04", "ELF": b"\x7fELF",
        "gzip": b"\x1f\x8b", "zlib": b"x\x9c",
        "LZ4 frame": b"\x04\x22\x4d\x18",
    }
    hits = [label for label, sig in signatures.items() if data.startswith(sig)]
    lines.append("- Leading signature: " + (", ".join(hits) if hits else "no common container signature"))
    vecs = vector_candidates(data)
    lines.append(f"- Cortex-M vector-table candidates: {len(vecs)}")
    for off, sp, reset, base in vecs[:12]:
        lines.append(f"  - offset 0x{off:X}: initial SP 0x{sp:08X}, reset 0x{reset:08X}, candidate base 0x{base:08X}")
    if len(data) >= 4096:
        win = 4096
        samples = [(i, entropy(data[i:i+win])) for i in range(0, len(data)-win+1, win)]
        high = [(i,e) for i,e in samples if e >= 7.75]
        low = [(i,e) for i,e in samples if e <= 5.5]
        lines.append(f"- 4 KiB entropy windows: {len(samples)}; high-entropy (>=7.75): {len(high)}; low-entropy (<=5.5): {len(low)}")
        if high[:8]:
            lines.append("  - High-entropy offsets: " + ", ".join(f"0x{o:X} ({e:.2f})" for o,e in high[:8]))
    ss = strings(data)
    useful = [s for s in ss if re.search(r"tft|display|screen|lcd|font|draw|bitmap|image|music|media|ble|uart|spi|i2c|lvgl|gui|frame|icon|battery|speed|ninebot|segway", s, re.I)]
    lines.append(f"- Printable strings (min 5 chars): {len(ss)}")
    lines.append("- Relevant-looking strings:")
    lines.extend(f"  - {s[:180]}" for s in useful[:100])
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("package", type=Path)
    ap.add_argument("--out", type=Path, default=Path("f3-ble-static-report.md"))
    args = ap.parse_args()
    raw = args.package.read_bytes()
    sections = [
        "# F3/F3 Pro stock BLE firmware static triage",
        "",
        "> Offline inspection only. No scooter connection, writes, patching, or flashing.",
        "",
        f"- Input: {args.package.name}",
        f"- Package size: {len(raw):,} bytes",
        f"- Package SHA-256: {sha256(raw)}",
        "",
    ]
    if zipfile.is_zipfile(args.package):
        with zipfile.ZipFile(args.package) as zf:
            sections.append("## Archive members")
            for info in zf.infolist():
                sections.append(f"- {info.filename} — {info.file_size:,} bytes (compressed {info.compress_size:,})")
            sections.append("")
            for info in zf.infolist():
                if info.is_dir() or info.file_size > 32 * 1024 * 1024:
                    continue
                blob = zf.read(info)
                if info.filename.lower().endswith((".bin", ".img", ".hex", ".dat")) or len(blob) > 256 * 1024:
                    sections.extend(["", analyse_blob(info.filename, blob), ""])
    else:
        sections.extend(["## Firmware image", "", analyse_blob(args.package.name, raw), ""])
    sections.extend([
        "## Interpretation limits",
        "- High entropy may mean compression, encryption, or dense machine code; entropy alone cannot distinguish them.",
        "- A vector-table candidate is a heuristic, not proof of MCU architecture or load address.",
        "- No display command is valid until its handler and payload semantics are independently established.",
        "- Do not transmit guessed frames to the scooter.",
    ])
    args.out.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(args.out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
