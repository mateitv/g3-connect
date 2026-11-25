# Segway Mobility 6.10.13 protocol investigation

Date: 2026-11-25

## Scope

Inspected the user-provided Segway Mobility 6.10.13 APK export (base APK plus ABI/configuration splits), emphasizing native arm64 libraries and visible code/resources. Static analysis only; no scooter was connected and no commands were sent.

## Confirmed findings

- The base APK contains a small visible DEX with a Netease wrapper application entry point. Most app implementation is not represented as ordinary readable Java/Kotlin classes in that DEX; this limits static inspection.
- The arm64 split includes libnbcrypto.so and libnbenc_ffi.so.
- libnbcrypto.so contains JNI entry points under cn.ninebot.nbcrypto.NbEncryption for hash, crypto initialization/reset, key setup, encryption and decryption.
- libnbenc_ffi.so contains is_frame_header_AA55, nb_encrypt, and nb_decrypt symbols. This directly establishes that the bundle includes a Ninebot frame/encryption helper with an AA55 frame-header check. It does not identify the TFT display command or payload schema, nor prove this helper is the F3 Pro display transport.
- libhud_protocol.so exports a JNI symbol for net.easyconn.carman.hud.protocol.utils.RSAUtils_getLicensePubKey. Its naming and associated resources identify it as an EasyConnect/Carbit automotive HUD licensing helper, not evidence of the scooter TFT protocol.
- Resources mention Bluetooth HUD, screen mirroring, and quick music controls. These refer to phone/car HUD integration and must not be conflated with the scooter 2.4-inch TFT.
- Existing NinebotEnhance source already has a Canvas music card, interpolated playback position, title/artist, and a configurable 240x320 portrait/half-screen rendering path. Its 240x320 Bluetooth MPEG2 profile still needs hardware validation.

## What remains unknown

- Which Bluetooth GATT service/characteristic or application command transfers display frames to the F3 Pro TFT.
- Whether F3 Pro firmware accepts third-party frame payloads, and whether it requires authenticated/encrypted frames beyond generic AA55 framing.
- Whether NinebotEnhance international-app hooks work with Segway Mobility 6.10.13 and the F3 Pro specifically.
- Exact card placement and legibility on this TFT firmware/hardware revision.

## Safe next investigation

1. Compare a read-only Bluetooth HCI snoop capture of a normal official-app connection with one where the official app is showing its own supported dashboard content. Do not inject writes or replay captured commands.
2. Identify GATT service/characteristic UUIDs and packet boundaries from the capture; correlate only with public Ninebot frame definitions and the AA55 helper.
3. Keep music HUD rendering isolated from scooter control commands. Do not change turn signals, mode controls, speed limits, or firmware.
4. Only attempt a display payload after the exact protocol and a harmless, reversible test frame are established.

## Prototype status

The phone-side music-session bridge and 240x320 Canvas preview are already verified in G3 Connect. This investigation does not establish end-to-end transfer to the scooter TFT. The HTML mockup is a layout preview only, not a scooter-connected build.