#!/usr/bin/env python3
"""Offline inspector for plaintext Ninebot 0x5A 0xA5 frames.

Never connects to or writes to a scooter. Paste a hex dump captured from an
existing authorized diagnostic session. Encrypted frames remain opaque.
"""
from __future__ import annotations
import argparse
import re
from dataclasses import dataclass

@dataclass
class Frame:
    offset: int
    total: int
    length: int
    source: int
    destination: int
    command: int
    argument: int
    payload: bytes
    checksum: bytes
    checksum_status: str

def parse_frames(data: bytes) -> list[Frame]:
    frames: list[Frame] = []
    i = 0
    while i + 7 <= len(data):
        start = data.find(b"\x5a\xa5", i)
        if start < 0 or start + 7 > len(data):
            break
        plen = data[start + 2]
        parsed = None
        # Newer plaintext form observed in community x3-series tooling:
        # 2-byte complement-of-sum checksum, total LEN + 9.
        n2 = plen + 9
        if start + n2 <= len(data):
            raw = data[start:start+n2]
            check = (0xFFFF - (sum(raw[2:7+plen]) & 0xFFFF)) & 0xFFFF
            if raw[-2:] == bytes((check & 0xFF, check >> 8)):
                parsed = (raw, raw[7:7+plen], raw[-2:], "MATCH: 16-bit complement checksum")
        # Classic Ninebot form: total LEN + 8. Checksum variants differ by
        # generation, so parse it but deliberately do not claim validation.
        if parsed is None:
            n1 = plen + 8
            if start + n1 <= len(data):
                raw = data[start:start+n1]
                parsed = (raw, raw[7:7+plen], raw[-1:], "NOT VALIDATED: legacy checksum variant")
        if parsed is None:
            break
        raw, payload, checksum, status = parsed
        frames.append(Frame(start, len(raw), plen, raw[3], raw[4], raw[5],
                            raw[6], payload, checksum, status))
        i = start + len(raw)
    return frames

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hex", help="hex bytes, e.g. '5A A5 02 04 01 01 00 ...'")
    args = ap.parse_args()
    compact = re.sub(r"[^0-9a-fA-F]", "", args.hex)
    if len(compact) % 2:
        ap.error("hex input must contain complete bytes")
    frames = parse_frames(bytes.fromhex(compact))
    if not frames:
        print("No complete plaintext 5A A5 frames found (or capture is encrypted).")
        return
    for n, f in enumerate(frames, 1):
        print(f"Frame {n} @+0x{f.offset:X} total={f.total}")
        print(f"  LEN={f.length} SRC=0x{f.source:02X} DST=0x{f.destination:02X}")
        print(f"  CMD=0x{f.command:02X} ARG/index=0x{f.argument:02X}")
        print(f"  DATA={f.payload.hex(' ').upper() or '(empty)'}")
        print(f"  checksum={f.checksum.hex(' ').upper()} [{f.checksum_status}]")
        if f.source == 0x23 or f.destination == 0x23:
            print("  note=0x23 appears as a TFT/board address in one x3-series community project; verify per model.")

if __name__ == "__main__":
    main()
