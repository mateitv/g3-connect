#!/usr/bin/env python3
"""Decrypt a Ninebot v3 ZIP firmware package using the public NinebotTEA format.

Read-only/offline utility. It extracts and decrypts a local package; it does not
connect to, write to, or flash a scooter.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

DEFAULT_KEY = bytes.fromhex("fe801cb2d1ef41a6a41731f5a06824f0")
DELTA = 0x9E3779B9
MASK = 0xFFFFFFFF


def checksum(data: bytes) -> int:
    total = sum(int.from_bytes(data[i:i + 4], "little") for i in range(0, len(data), 4))
    total = ((total >> 16) & 0xFFFF) | ((total & 0xFFFF) << 16)
    return total ^ MASK


def update_key(key: list[int]) -> list[int]:
    raw = b"".join(word.to_bytes(4, "little") for word in key)
    raw = bytes((value + index) & 0xFF for index, value in enumerate(raw))
    return [int.from_bytes(raw[i:i + 4], "little") for i in range(0, 16, 4)]


def decrypt_block(y: int, z: int, key: list[int]) -> tuple[int, int]:
    total = (DELTA * 32) & MASK
    for _ in range(32):
        z = (z - (((y << 4) + key[2]) ^ (y + total) ^ ((y >> 5) + key[3]))) & MASK
        y = (y - (((z << 4) + key[0]) ^ (z + total) ^ ((z >> 5) + key[1]))) & MASK
        total = (total - DELTA) & MASK
    return y, z


def decrypt(data: bytes, key_bytes: bytes = DEFAULT_KEY) -> bytes:
    if not data or len(data) % 8:
        raise ValueError("Encrypted firmware length must be a non-zero multiple of 8 bytes")
    key = [int.from_bytes(key_bytes[i:i + 4], "little") for i in range(0, 16, 4)]
    iv = 0
    processed = 0
    out = bytearray()
    for offset in range(0, len(data), 8):
        if processed == 1024:
            key = update_key(key)
            processed = 0
        block = int.from_bytes(data[offset:offset + 8], "little")
        y, z = decrypt_block(block & MASK, block >> 32, key)
        plain = (((z << 32) | y) ^ iv)
        out.extend(plain.to_bytes(8, "little"))
        iv = block
        processed += 8
    if len(out) < 4:
        raise ValueError("Decrypted payload is too short")
    provided = int.from_bytes(out[-4:], "little")
    calculated = checksum(out[:-4])
    if provided != calculated:
        raise ValueError(f"Ninebot checksum mismatch: got {provided:08x}, expected {calculated:08x}")
    return bytes(out[:-4])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("package", type=Path)
    ap.add_argument("--out", type=Path, default=Path("f3_ble_decrypted.bin"))
    ap.add_argument("--key", default=DEFAULT_KEY.hex(), help="16-byte key as 32 hex characters")
    args = ap.parse_args()
    key = bytes.fromhex(args.key)
    if len(key) != 16:
        ap.error("--key must be exactly 16 bytes (32 hex characters)")
    with zipfile.ZipFile(args.package) as zf:
        names = zf.namelist()
        if "info.json" not in names:
            raise SystemExit("No info.json found in firmware ZIP")
        info = json.loads(zf.read("info.json"))
        firmware = info.get("firmware", {})
        if firmware.get("type") != "BLE":
            raise SystemExit(f"Expected BLE package, got {firmware.get('type')!r}")
        encrypted_name = next((n for n in names if n.lower().endswith(".enc")), None)
        if not encrypted_name:
            raise SystemExit("No .enc payload found")
        encrypted = zf.read(encrypted_name)
        expected_md5 = firmware.get("md5", {}).get("enc", "").lower()
        actual_md5 = hashlib.md5(encrypted).hexdigest()
        if expected_md5 and actual_md5 != expected_md5:
            raise SystemExit(f"Encrypted payload MD5 mismatch: {actual_md5} != {expected_md5}")
        plain = decrypt(encrypted, key)
    args.out.write_bytes(plain)
    print(f"Model: {firmware.get('model')}")
    print(f"Version: {firmware.get('displayName')}")
    print(f"Encrypted payload MD5 verified: {actual_md5}")
    print(f"Decrypted size: {len(plain):,}")
    print(f"Decrypted SHA-256: {hashlib.sha256(plain).hexdigest()}")
    print(f"Output: {args.out}")


if __name__ == "__main__":
    main()
