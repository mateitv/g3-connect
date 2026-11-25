#!/usr/bin/env python3
"""Extract the stock F3/F3 Pro BLE firmware's printable media-related strings.

Offline inventory only. This script does not disassemble code, infer packet
semantics, connect to a scooter, or modify firmware.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

GROUPS = {
    "media_control": (
        b"bts_media_enable", b"bts_media_next_song",
        b"bts_media_previous_song", b"bts_media_play",
        b"bts_media_vol_up", b"bts_media_vol_down",
    ),
    "media_status_and_connection": (
        b"bts_media_status_change_notify", b"bts_media_connect",
        b"bts_media_connect_status_change_notify",
        b"bts_media_disconnect_timer_handler",
    ),
    "avrcp": (
        b"bts_avrcp_controller_nextsong",
        b"bts_avrcp_controller_presong",
    ),
    "nearby_app_callbacks": (
        b"btapp_navi_data_received", b"ninebot_gatt_server",
    ),
    "display": (
        b"update_display_content", b"write_cb tft not ready",
        b"lvgl_view", b"lv_draw_label", b"st7735",
        b"Display initialized.", b"Uart dispatcher",
    ),
}
METADATA_TERMS = (
    b"artist", b"album", b"getelementattributes", b"element_attributes",
    b"playing_time", b"track_number", b"playback_position",
)


def extract_strings(data: bytes, minimum: int = 5):
    pattern = rb"[\\x20-\\x7e]{" + str(minimum).encode() + rb",}"
    return [(m.start(), m.group().decode("ascii", "replace"))
            for m in re.finditer(pattern, data)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path, help="decrypted RAW4TFT image")
    parser.add_argument("--minimum", type=int, default=5)
    args = parser.parse_args()
    data = args.image.read_bytes()
    strings = extract_strings(data, args.minimum)
    lower = [(offset, value, value.lower()) for offset, value in strings]

    print(f"Image bytes: {len(data):,}")
    print("Inventory only: string presence does not establish runtime behavior.")
    for group, needles in GROUPS.items():
        print(f"\\n[{group}]")
        found = 0
        for offset, value, folded in lower:
            if any(needle.decode().lower() in folded for needle in needles):
                print(f"0x{offset:06X}  {value}")
                found += 1
        if not found:
            print("(none)")

    print("\\n[metadata_keyword_scan]")
    for term in METADATA_TERMS:
        hits = [(offset, value) for offset, value, folded in lower
                if term.decode() in folded]
        print(f"{term.decode()}: {len(hits)} match(es)")
        for offset, value in hits[:10]:
            print(f"  0x{offset:06X}  {value}")


if __name__ == "__main__":
    main()
