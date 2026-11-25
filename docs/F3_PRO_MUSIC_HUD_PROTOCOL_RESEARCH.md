# F3 Pro music-HUD protocol research

**Status: F3/x3 display transport architecture and a navigation command family identified; a general-purpose music-text command is still unknown.**
**No scooter writes, firmware changes, app replacement, or hardware modifications are part of this prototype.**

## Grounded findings from F3/x3 community source

The public `MacintoshKeyboardHacking/segMod` project explicitly says it was developed on F3 and GT3 Pro models. Its current `myBLEv4` design intercepts traffic between the BLE module and VCU while retaining the stock display.

- The x3 architecture notes say the BLE module handles Bluetooth and the LCD/TFT. It connects to the VCU over a 3.3 V two-wire UART using Ninebot frames. A separate 1.8 V pair is described as BLE-sourced debug output.
- `myBLEv4.ino` opens two UARTs at 115200 baud and routes packets between BLE and VCU. Its parser validates the 16-bit complement-of-sum checksum.
- `x3regs.h` explicitly defines `ECU_TFT = 0x23`, `ECU_VCU = 0x16`, and `ECU_BLE = 0x04`. The earlier generic board-ID list was ambiguous because some unrelated examples reuse 0x23 for another board. For this x3 source, use the explicit `x3regs.h` mapping rather than mixing model families.
- The same header identifies a TFT navigation command family: `CMD_TFT_setNavi = 0x71`, with subcommands `0x00` start, `0x01` distance, `0x03` info, `0x10` road, `0x24` next road, `0x38` text, and `0xff` exit. It also identifies `TFT_SUBbase = 0xfe` for subscription-related traffic.
- The source comments describe VCU-to-TFT (`0xfe`) realtime reports and parses subscription parameters. This is useful evidence about how the stock display receives data.

### Public x3 debug trace found

I also found `logs/BLEuart2-debugx-log.txt` in the segMod repository. It is a public BLE-module debug trace, not an Android `btsnoop_hci.log` and not a clean raw packet capture. It records repeated subscription events with source `0x16` (VCU), destination `0x23` (TFT), command `0x03`, index `0xfe`, and a 35-byte payload. It also records writes to display-related indexes such as `0x60`, `0x62`, and `0xd5`. The log contains no track title, artist, or music-metadata events. This gives us real x3 display-traffic evidence, but not the music command we need.

### Cross-check against a second G3 Connect implementation

A separate public G3 Connect Android implementation also sends the `0x23 / 0x71` command family for navigation only: distance at index `0x01`, current/next road strings at `0x10` and `0x24`, and maneuver information at `0x03`. Its road-string encoder uses UTF-8, truncates safely to 39 bytes, and appends a NUL terminator. This is an independent implementation of the navigation channel, not a music HUD.

### Critical limitation for our music HUD

The `0x71 / 0x38` item is explicitly named as **navigation text**. It is not evidence of a general music overlay or a separate music-text API. Since the user does not want music metadata written into navigation fields, we will not repurpose this command. We also will not send it experimentally.

The source also lists `TFT_Display = 0x62` and `TFT_Alert = 0xd5`, but their semantics and payloads are not established. They are research leads only; we will not write to them. The sources do not yet expose a supported command for arbitrary music title/artist text or a progress bar. That remains the key unknown.

## Phone-to-scooter BLE is a separate layer

The official-app BLE protocol documentation describes the phone-to-BLE-module link: Ninebot framing, a custom Ninebot GATT service, AES-128-based Encryption2, and a PRE_COMM / SET_PWD / AUTH handshake. This is distinct from the internal BLE-to-VCU UART link above. A generic Nordic UART UUID or a legacy G30 register map is not sufficient evidence for F3 TFT rendering.


### Additional BLE/media and audio leads checked

The x3 register header also names:

- `CMD_BLE_mediaEnable = 0x10` under the BLE command family (`CMD_BLE = 0x6f)). This is a lead for a BLE media-related feature, but the public source only defines the constant; I found no call site or documented payload/semantics. It is not proof that the TFT accepts song metadata.
- `CMD_AUDIO_BEGIN = 0x76`, `CMD_AUDIO_WR = 0x77`, and `CMD_AUDIO_CRC = 0x78` are described as audio upload/chunk/CRC commands. These look like uploading an audio asset to the scooter, not sending live media-session metadata. They are not suitable for track title, artist, or playback progress.
- `TFT_Display = 0x62` is explicitly marked unknown by the source author (with speculative display-state values). `TFT_Alert = 0xd5` is named but has no published payload definition. Neither is safe to repurpose or probe blindly.

The debug trace includes writes to `0x62` and `0xd5`, but the observed values do not establish a music function. No write will be attempted.

### Firmware research status

ScooterHacking announced on 15 November 2026 that its X3 SHFW work includes a fully rewritten BLE/display firmware for F3/F3 Pro and other X3 models, with public beta targeted before the end of 2026. This is potentially the most promising future source of an open, model-aware TFT implementation. It is not a solution we should install or flash now: the project is still pre-beta in that announcement, and the user has explicitly asked to keep the current scooter firmware and app setup intact.

## What this means for the project

Already verified:
- Android media-session detection for Spotify and YouTube Music.
- Song title, artist, playback position, duration, and progress rendering in the G3 Connect app preview.
- The phone-side preview's NOW PLAYING flash and progress interpolation.

Still unverified:
- Whether the stock F3 TFT firmware exposes a non-navigation music text/card command.
- Whether the official Segway app transmits music metadata to the F3 TFT at all, or whether the current music display seen on other models is a different firmware feature.
- The exact app-to-TFT command payload and any length/encoding limits.

## Offline tooling

`tools/f3_ble_frame_inspector.py` parses plaintext `5A A5` frames and extracts length, source, destination, command, argument/index, and payload. It validates the 16-bit complement checksum used by the x3 source. Legacy checksum variants are labelled unvalidated. Encrypted frames remain opaque.

Example:

```sh
python tools/f3_ble_frame_inspector.py "5A A5 ..."
```

The tool does not scan, connect, pair, authenticate, or transmit anything.

## Next research path

1. Inspect the x3 source's TFT navigation handling and subscription flow for evidence of any separate, non-navigation text/card command.
2. Compare that with the official Segway app's available music-session integration and any display-transfer implementation.
3. Keep any future sender disabled by default and restrict it to a positively identified display-only command. Do not touch control, brake, throttle, speed-limit, or firmware registers.

A real F3 capture would still be the strongest final verification, but this research step does not require the scooter to be physically present.

## Sources

- `https://github.com/MacintoshKeyboardHacking/segMod` — explicitly developed on F3/GT3 and describes retaining the stock display.
- `https://github.com/MacintoshKeyboardHacking/segMod/blob/main/myBLE4/myBLEv4.ino` — UART routing, Ninebot frame parsing, checksum, VCU/TFT subscription handling.
- `https://github.com/MacintoshKeyboardHacking/segMod/blob/main/myBLE4/x3regs.h` — x3 board IDs and TFT navigation command/subcommand definitions.
- `https://github.com/MacintoshKeyboardHacking/segMod/blob/main/logs/BLEuart2-debugx-log.txt` — public BLE-module debug trace with VCU-to-TFT subscription events; not a phone HCI snoop capture.
- `https://github.com/sfw9/g3-connect/blob/main/android-bridge/src/de/g3connect/maps/NinebotClient.java` and `NaviPacket.java` — independent implementation showing that the 0x71 family carries navigation guidance and UTF-8 road strings.
- `https://nootnooot.codeberg.page/segway-ninebot-ble/` — phone-to-BLE-module framing and Encryption2 handshake.
