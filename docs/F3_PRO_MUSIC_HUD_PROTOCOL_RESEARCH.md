# F3 Pro music-HUD protocol research

**Status: transport architecture identified; music-text command not yet identified.**
**No scooter writes, firmware changes, or app replacement are part of this prototype.**

## What is now grounded

1. The F3 belongs to Segway's x3 platform. The public `segMod` project states it was developed on GT3 Pro and F3, and describes the BLE module as responsible for Bluetooth and the LCD/TFT display.
2. On F3/G3/GT3, the BLE module is connected to the VCU through a 3.3 V UART carrying Ninebot protocol frames. The x3-series control cable uses CAN between VCU and motor controller; the phone does not simply address the TFT as a generic BLE peripheral.
3. The same project documents an internal 10-pin header exposing the UART pair and a separate debug pair. Its source contains a Ninebot `5A A5` frame parser/router and maps traffic to multiple ECU/board IDs. A board ID appearing in one community source is not enough to infer a text-render command.
4. The current official Segway app BLE protocol is separately documented by the NootNooot interoperability project: `5A A5` frames, a custom Ninebot GATT service, AES-128-based Encryption2, and a PRE_COMM / SET_PWD / AUTH handshake. This is the phone-to-BLE-module link, not the internal BLE-to-VCU display command.

## What this means for the music HUD

The remaining unknown is not the Android media session (already verified in the G3 Connect preview). It is the specific x3 BLE-module command or subscription that carries display/navigation/HUD content between the phone and the TFT. We must identify that from a real F3 Pro capture or a model-matched firmware/app trace. A G30 register map, generic NUS UUID, or an address copied from a different x3 project is not sufficient.

## Prototype added

`tools/f3_ble_frame_inspector.py` is an offline-only first-stage decoder for plaintext `5A A5` captures. It extracts frame length, source, destination, command, argument/index and payload. It checks the 16-bit complement checksum variant used by one public x3-series implementation; legacy checksum variants are labelled unvalidated. Encrypted frames remain opaque.

Example:

```sh
python tools/f3_ble_frame_inspector.py "5A A5 ..."
```

The tool does not scan, connect, pair, authenticate, or transmit anything.

## Next evidence needed

A Bluetooth HCI snoop capture from the user's own F3 Pro while the official Segway app performs a harmless, ordinary action that updates the TFT (for example, starting/stopping navigation). Comparing those packets with the app's BLE traffic can isolate the display/HUD channel. Only after that command is identified should we implement a sender, initially behind a disabled feature flag and with no control-register writes.

## Sources

- `https://github.com/MacintoshKeyboardHacking/segMod` — x3-series architecture and F3/GT3 development target.
- `https://github.com/MacintoshKeyboardHacking/segMod/blob/main/myBLE4/myBLEv4.ino` — UART routing, `5A A5` packet parsing, and ECU maps.
- `https://nootnooot.codeberg.page/segway-ninebot-ble/` — official-app BLE framing, service, and Encryption2 handshake.
