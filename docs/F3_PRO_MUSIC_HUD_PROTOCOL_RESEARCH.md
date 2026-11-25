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



### Cross-model protocol trap identified

I checked a separate GT3 Pro BLE protocol reference as a cross-check. It documents a different board map (including a TFT address of `0x09` and a BLE address of `0x21`), while the F3/x3 `segMod` source maps the TFT as `0x23` and BLE as `0x04`. This is a useful warning: even scooters in the broader X3 family must not be assumed to share the same board-address table or command payloads. Our implementation target remains the F3 Pro, and we will not copy GT3 Pro packet addresses into it.

Source checked: `https://github.com/djensenius/gt3pro/blob/main/docs/gt3-pro-ble-protocol.md` (GT3 Pro only; used as a contrast, not as F3 command documentation).

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

### Source-wide check of the BLE media command

I fetched the complete current `myBLE4/myBLEv4.ino` and `myBLE4/x3regs.h` from the F3/x3 `segMod` source and searched both files for `CMD_BLE_mediaEnable`, `CMD_AUDIO_*`, and the TFT display/alert identifiers.

Results:
- `CMD_BLE_mediaEnable = 0x10` appears only as a constant definition in `x3regs.h`; there is no use of that constant in the complete `myBLEv4.ino` sketch. The public implementation therefore gives us no request frame, payload, response, or indication that this command is used to deliver live track metadata.
- The three `CMD_AUDIO_*` definitions are explicitly commented as audio upload start, audio data chunk, and CRC verification. This reinforces that they are asset-transfer commands, not a documented live metadata channel.
- `TFT_Display = 0x62` remains explicitly marked unknown, and `TFT_Alert = 0xd5` still has no payload definition. The main sketch's only matching TFT-subscription reference is a commented-out diagnostic line; it does not reveal a supported write interface.

This narrows the next step: do not build a sender around `0x6f/0x10` or `0x23/0x62` based on names alone. The next useful evidence would be an implementation or trace that shows a real request/response and a TFT-side effect for a display-only music operation. Until then, the music-to-TFT transport remains unknown.

### Deeper inspection: what the TFT subscription channel actually carries

I followed the relevant code paths in the complete `segMod` F3/X3 sketch instead of treating the `0xfe` packet as a generic display API.

- The sketch identifies packets addressed to TFT `0x23`, index `0xfe`, as the TFT subscription update. It decodes that payload using a previously received subscription map, where each entry is a 32-bit subscription ID plus a bit length.
- The decoded values are then unpacked into the subscription-value table. The example IDs in `x3regs.h` are vehicle telemetry/state: speed, remaining distance, trip distance, battery percentage, charging, gear mode, headlight, TCS/SABS and related riding flags.
- The old compatibility subscription request `bSub` is a BLE-to-VCU request containing those subscription IDs and bit widths. It is not a request for arbitrary text or a music card.
- In the live packet loop, the author modifies selected fields in the VCU-to-TFT `0xfe` subscription payload (for example, remaining range and overspeed-related bits) and forwards the packet. The code does not construct a new music display object, title string, artist string, or playback-progress field.
- The public debug trace independently shows repeated `on_pub_sub` events with source 22 (decimal, VCU `0x16`), destination 35 (decimal, TFT `0x23`), command 3, index 254 (`0xfe`), and a 35-byte data field. This matches the telemetry-subscription path. The trace does not include the actual payload bytes, so it cannot identify any undocumented field beyond that.

**Conclusion:** `0xfe` is a packed subscription/telemetry update path, not a documented general-purpose TFT text/card interface. We should not try to squeeze track text into its bit fields. The known `0x71` navigation family remains separate and is also off-limits for music metadata. No safe, documented F3 TFT music-display write path has emerged from this source.

Sources inspected:
- `myBLE4/myBLEv4.ino`: `subMap()`, `subSet()`, `doRXdecode()`, and the main packet-forwarding loop around the `0x23 / 0xfe` handler.
- `myBLE4/x3regs.h`: `ECU_TFT`, `TFT_SUBbase`, subscription ID definitions, and the `bSub` subscription request.
- `logs/BLEuart2-debugx-log.txt`: repeated `on_pub_sub` events with the VCU-to-TFT address/command/index tuple.

### New source lead: open X3 VCU implementation (F3 build included)

I found and inspected the public `hp197/x3-vcu-fw` source. Its README explicitly provides build targets for `gt3`, `zt3`, and `f3`, and documents the VCU's USART link to the BLE/dashboard module. This is substantially more useful than a generic legacy Ninebot protocol reference because it is written for the X3 platform.

What its code establishes:
- The VCU's USART2 link to the BLE/dashboard node uses Ninebot `5A A5` frames at 115200 baud. The VCU address is `0x16`; the BLE/dashboard app node is `0x23`.
- The app-node handler supports configuration-register reads/writes, registration/OTA operations, and a few explicit state notifications. It does not expose an arbitrary TFT drawing API.
- A separate control-node command (`cmd 0x04, arg 0x20`) updates the VCU's display/ride-mode gesture state. The source does not describe this as a text or media-display command.
- The documented app-node `cmd 0x03, arg 0xD2` writes a distance-related state value; it is not a free-form string channel.
- The source's own scope places display and Bluetooth functions in the BLE module. It implements the VCU side of that link, not the BLE module's TFT rendering engine.

Important distinction: this is an independent, open-source VCU firmware implementation for the X3 platform, not Segway's original proprietary BLE/display source. It can tell us what the VCU side of the F3 link expects and emits, but it cannot reveal the original TFT renderer or prove that an undocumented display command exists.

Sources:
- `hp197/x3-vcu-fw` README: F3 build target and VCU/BLE link architecture.
- `include/usart.h`: 5A A5 framing, 115200 baud, VCU/BLE node addresses.
- `include/ninebot.h` and `src/ninebot.c`: app-node and control-node command handlers.
- Repository: https://github.com/hp197/x3-vcu-fw

### Current conclusion and next research target

The evidence now covers both sides of the *known* VCU/TFT telemetry path:
1. `0x23 / 0xFE` is packed VCU-to-TFT subscription telemetry.
2. `0x23 / 0x71` is the navigation-message family.
3. The open X3 VCU implementation exposes app/configuration and control messages, but no arbitrary text/card renderer.
4. The phone-side Segway 6.10.13 package contains an EasyConnect/Carbit automotive HUD integration, but that is not evidence of a scooter TFT music channel.

The missing component is specifically the F3 BLE module's display firmware / TFT rendering implementation. ScooterHacking announced on 15 November 2026 that its X3 SHFW effort includes a completely rewritten BLE/display firmware for F3/F3 Pro, with a public beta targeted before the end of 2026. That source or its release may become the first credible route to a real custom TFT renderer. This is a research lead only; no firmware installation or flashing is being proposed.

### Firmware archive discovery: original F3/F3 Pro BLE binaries are publicly mirrored

A separate public archive, `Rexzy67/X3-Firmware`, contains stock F3/F3 Pro BLE firmware packages:
- `0.3.12`
- `0.3.14`
- `0.4.0`

The archive lists both ZIP packages and raw `FIRM_*.bin` files under `F3-F3PRO/Stock/BLE`. This is the first concrete firmware artifact lead for the missing BLE/display component. It is **binary firmware, not source code**, and its presence does not establish that it is unpacked, unencrypted, or directly suitable for disassembly. I have not flashed or modified any firmware.

Repository path: https://github.com/Rexzy67/X3-Firmware/tree/main/F3-F3PRO/Stock/BLE

The next technical step is static inspection of a locally available stock BLE image (identify container/header, image boundaries, MCU architecture and executable regions, then look for display-driver and command-dispatch code). The VCU source alone cannot answer this because the TFT renderer is on the BLE module.

### Stock BLE 0.4.0 decrypted successfully (major reverse-engineering milestone)

The read-only CI workflow downloaded the public F3/F3 Pro stock BLE 0.4.0 package and inspected its archive. The package contains:
- `FIRM.bin.enc` (1,835,488 bytes)
- `info.json`, which identifies model `f3`, component `BLE`, version `0.4.0`, and marks the payload as encrypted.

The encrypted payload MD5 in `info.json` was verified. The payload was then decrypted using the published NinebotTEA CBC/rolling-key/checksum format with the public default key and classic TEA variant. The final Ninebot checksum matched exactly. This is strong verification that the decrypted output is valid, not merely a guessed decryption.

Verified decrypted image:
- Size: 1,835,484 bytes
- SHA-256: `6e51fad22b5d8b5045a9ab8ae27df64ab173641372d14d4ed94996dd38b1a635`
- Image magic: `RAW4TFT`
- Vector table offset indicated by the image header: `0x400`
- Initial stack pointer: `0x20080000`
- Reset vector: `0x0C028571` (Thumb entry at `0x0C028570`)
- Mapping base inferred by matching reset-vector address to the corresponding file offset: `0x0C000000`
- Reset handler file offset: `0x28570`

The image is no longer opaque ciphertext: its reset vector and handler bytes decode as Thumb/Thumb-2-looking code. This establishes a concrete path into the BLE/display firmware. It does **not yet** identify the MCU model, TFT driver, GUI library, or any music command. Those need to be established from the disassembly and peripheral initialization.

New read-only tooling committed:
- `tools/decrypt_ninebot_x3_package.py` — verifies the package MD5, decrypts NinebotTEA, and verifies the embedded checksum.
- `tools/disassemble_f3_ble_image.py` — uses Capstone to disassemble the reset handler and in-image vector handlers.
- `tools/analyze_f3_ble_firmware.py` — archive/image triage, hashes, entropy and strings.
- `.github/workflows/f3-ble-static-analysis.yml` — downloads and inspects the public image in CI; no scooter connection or flashing.

The next reverse-engineering target is the decrypted BLE image's startup path, interrupt vectors, peripheral setup, and references to SPI/display buffers. We must identify the renderer and its message ingress before designing a music metadata packet. The known navigation `0x71` and telemetry `0xFE` channels remain excluded.

### Address-map status: header/vector offset distinguished from load base

The image header contains a `0x400` field, and the initial stack/reset-vector pair is at file offset `0x400`. A previous pass treated `0x0C000400` as the load base because that offset made several vector targets land on clean-looking function prologues. That was only a heuristic and was not enough to establish the mapping. It is superseded.

The current working interpretation is:
- File offset `0x400` is the vector-table location.
- The secure flash alias/load base is provisionally `0x0C000000`.
- Reset vector `0x0C028571` therefore maps provisionally to file offset `0x28570`.

The disassembler default has been returned to `0x0C000000`. The first halfword at the reset target is not decoded by the current Capstone/LLVM builds, so the reset-entry interpretation is still unresolved. Do not treat either candidate mapping as final until it is cross-checked against more reset/startup evidence and the hardware memory map.

### Additional firmware disassembly findings and mapping caution

The decrypted image's vector table contains 14 distinct in-image Thumb targets. Several targets decode as ARMv8-M TrustZone-style entry/exit code, including `BXNS`/`BLXNS` instructions. Other code uses `MSPLIM`, `BASEPRI`, and FPU register-save instructions. This points to a TrustZone-capable M-profile MCU with floating-point support; it is not enough by itself to name the exact chip.

The code also references peripheral address `0x40002000`. Its register access pattern is consistent with a timer peripheral (the STM32H5 reference map, for example, places TIM14 at this address), making an STM32H5-class device a candidate worth checking. This is **not** a confirmed part identification: a single matching peripheral base is insufficient, and the image's address mapping still needs confirmation from more startup/vector evidence.

A useful false-positive was eliminated: `0x42544400` is in the Cortex-M peripheral bit-band alias region, so it is not evidence of a TFT controller register block. The function that references it appears to manipulate bit-band state, not draw pixels.

The 0x400 header field and the vector-table position must not be conflated with the code load base. The disassembler now defaults to the secure flash alias base `0x0C000000`, while retaining the `0x400` vector-table file offset. This mapping remains a working hypothesis until the reset handler and additional vector targets are reconciled conclusively.

### Stock BLE firmware UI and media capabilities: verified string evidence

A scan of the successfully decrypted image found the following literal strings (file offsets shown in hex):

**Display/rendering stack**
- `0x0F0724`: `lvgl_view` (LVGL task/view name)
- `0x198830`: `Display initialized.`
- `0x1A94C4`: `st7735 Can't open /dev/gpio`
- `0x1A9B04`: `/dev/spi0`
- `0x1AD738`: `st7735_test`, with options to initialize the display and cycle display colours
- `0x1B2D6C`: `NOTICE:write_cb tft not ready !!`
- The image also contains LVGL drawing, font, image, canvas, PNG, GIF and LZO implementation strings, including source paths under `lvgl_lib/lvgl`.

This confirms the stock BLE image includes an LVGL UI stack and an ST7735 SPI display driver. The screen is not simply a passive text display; the firmware owns the renderer.

**Display data model / UI properties**
- `0x1A9538`: `navi_info`
- `0x1A961C`: `is_tft_start`
- `0x1A99CC`: `tft_upgrade_status`
- `0x1A9780`: `bt_music_connect_status`
- `0x1B27D4`: `DEBUG:update_display_content :%d %d`
- Nearby property names include `odo_or_trip`, `parking_state`, `tcs_onoff`, `ctl_headlight`, `ctl_turn_light`, `battery_total_sh`, and multiple riding-assistance states.

**Bluetooth media support**
- The image includes names for `bts_media_enable`, `bts_media_status_change_notify`, `bts_media_next_song`, `bts_media_previous_song`, `bts_media_play`, volume up/down, and AVRCP controller next/previous functions.
- Logs mention media enable/disable, media connection status, play/pause, previous song, next song, and media-control completion.
- UI resources include `popup_2lines_title_media_Misans_semibold_20_text` and the text `Media bluetooth paired`.

This is real media-control support, but it does **not** prove that the stock TFT receives or renders track title, artist, album, or playback progress. In the printable strings found so far, there are no clear song-title/artist/album/duration/progress labels or an obvious now-playing widget. The media UI evidence currently points to Bluetooth pairing/control status, not a complete music player HUD.

**UART/display transfer**
- Strings identify a UART dispatcher, UART channels, a `uart_process_task`, and a `write_cb` for the TFT.
- The dispatcher logs include source ID, destination ID, command and channel fields.
- No direct string cross-reference was recovered by the current ADR, MOVW/MOVT, and PC-relative LDR sweep. The firmware appears to use a nontrivial logging/symbol/resource layout, so the next step is to recover the dispatcher and its command table from control flow, not to guess command IDs.

### Consequence for the prototype

The original TFT has a real graphics stack, and the firmware has Bluetooth media-control functions. That is an encouraging hardware/software capability finding, but it is not yet a supported phone-to-TFT metadata path. The known navigation `0x71` and packed telemetry `0xFE` channels remain excluded. No guessed `0x62`, `0xD5`, or other undocumented payload will be sent.

A gold *phone-side* preview already exists and was verified with Spotify/YouTube Music metadata and playback progress. A gold *physical TFT* prototype is not ready: it requires either a documented stock-firmware command that safely updates a dedicated media UI, or a firmware-side change. The latter would violate the current no-flashing constraint, so it is not being treated as an acceptable test route.


### Stock BLE 0.4.0: first whole-image string and reference pass

I downloaded the successful CI artifact for run `45578654164` and inspected the decrypted image and generated reports locally. The image hash remains `6e51fad22b5d8b5045a9ab8ae27df64ab173641372d14d4ed94996dd38b1a635`.

The image contains a real set of display-stack strings:
- `lvgl_view`, `lv_draw_label`, and multiple LVGL source-path strings, confirming that LVGL code/resources are embedded in the stock BLE image.
- `st7735`, `/dev/spi0`, `/dev/gpio`, and `Display initialized.`, consistent with the TFT driver/display initialization path.
- `update_display_content` and `write_cb tft not ready`, which are useful display-update/logging leads.
- `Uart dispatcher` diagnostics, consistent with a UART message-dispatch service.

The image also contains a Bluetooth audio-control cluster of labels:
- `bts_media_enable`, `bts_media_next_song`, `bts_media_previous_song`, `bts_media_play`, `bts_media_vol_up`, `bts_media_vol_down`, and `bts_media_status_change_notify`.
- Related labels include `bts_avrcp_controller_nextsong`, `bts_avrcp_controller_presong`, `bts_media_connect`, and `bts_media_connect_status_change_notify`.
- Diagnostic strings describe a `bts_media_enable` operation and its completion result.

**Interpretation boundary:** this is evidence that the BLE firmware contains Bluetooth media-control / AVRCP-related functionality. It does not establish that the scooter TFT receives song title, artist, album, elapsed time, or duration. A scan of printable strings found no `artist`, `album`, `playback`, or `position` terms; `title` matches were unrelated UI asset names. These negative string results are suggestive, not proof that metadata is absent (metadata could be encoded, dynamically supplied, or handled without descriptive strings).

The updated whole-image Thumb string-xref scan resolved only three references, all associated with screen-backlight diagnostics. It did **not** resolve references to the media labels, `update_display_content`, or the TFT/LVGL labels. The scan is heuristic and may miss indirect calls, jump tables, relocation tables, data pointers, or code outside its assumed mapping. Therefore it cannot yet connect `bts_media_enable` or a UART message to the LVGL display update path.

The xref resolver was improved to accept pointers into the middle of candidate strings (commit `c4957694b76c8ccf7a21ed789f4917337fd16aee`). CI run `45578654164` completed successfully and produced artifact `15005118300`.

**Next reverse-engineering task:** establish the actual image memory/section mapping and recover references to the UART dispatcher and display update routine using a proper ARM/Thumb-aware function-boundary and data-reference analysis. In parallel, trace whether the AVRCP media-control cluster ever forwards metadata to an application/UI callback. Until that bridge is proven, do not implement or transmit a guessed TFT packet.
