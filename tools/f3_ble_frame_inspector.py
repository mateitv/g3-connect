#!/usr/bin/env python3
"""Offline inspector for plaintext Ninebot 0x5A 0xA5 frames.

This tool never connects to or writes to a scooter. Paste a hex dump captured
from an existing, authorized diagnostic session. Encrypted frames are reported
as opaque; this is not an encryption/authentication implementation.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass


@dataclass
class Frame:
    offset: int
    length: int
    source: int
    destination: int
    command: int
    argument: int
    payload: bytes
    checksum: bytes


def parse_frames(data: bytes) -> list[Frame]:
    frames: list[Frame] = []
    i = 0
    while i + 7 <= len(data):
        start = data.find(b"\x5a\xa5", i)
        if start < 0 or start + 7 > len(data):
            break
        payload_len = data[start + 2]
        # The classic plaintext packet is LEN + 8 bytes; newer plaintext
        # captures may carry a 2-byte checksum and be LEN + 9 bytes.
        candidates = (payload_len + 8, payload_len + 9)
        total = next((n for n in candidates if start + n <= len(data)), None)
        if total is None:
            break
        end = start + total
        raw = data[start:end]
        frames.append(Frame(
            offset=start,
            length=payload_len,
            source=raw[3],
            destination=raw[4],
            command=raw[5],
            argument=raw[6],
            payload=raw[7:-1] if total == payload_len + 8 else raw[7:-2],
            checksum=raw[-1:] if total == payload_len + 8 else raw[-2:],
        ))
        i = end
    return frames


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hex", help="hex bytes, e.g. '5A A5 02 04 01 01 00 ...'")
    args = ap.parse_args()
    compact = re.sub(r"[^0-9a-fA-F]", "", args.hex)
    if len(compact) % 2:
        ap.error("hex input must contain complete bytes")
    data = bytes.fromhex(compact)
    frames = parse_frames(data)
    if not frames:
        print("No complete plaintext 5A A5 frames found.")
        print("Encrypted frames cannot be decoded by this offline inspector.")
        return
    for n, f in enumerate(frames, 1):
        print(f"Frame {n} @+0x{f.offset:X}")
        print(f"  payload_len={f.length} src=0x{f.source:02X} dst=0x{f.destination:02X}")
        print(f"  cmd=0x{f.command:02X} arg/index=0x{f.argument:02X}")
        print(f"  payload={f.payload.hex(' ').upper() or '(empty)'}")
        print(f"  checksum_bytes={f.checksum.hex(' ').upper()}")
        print("  checksum_status=NOT_VALIDATED (variant-specific)")
        if f.destination == 0x23 or f.source == 0x23:
            print("  note=board 0x23 appears in community x3-series maps; TFT role is model/firmware-dependent")


if __name__ == "__main__":
    main()
