# Music HUD: phone prototype and F3 Pro TFT integration

## Current implementation in this repository

The Android bridge on `feature/music-hud-prototype` contains a phone-side 240×320 preview:

- Android media sessions are read locally by `MapsListener` (Spotify, YouTube Music, and other players that publish a media session).
- `MusicState` holds title, artist, duration, playback state, position and playback speed.
- `MusicProgress` interpolates position from Android's last position-update timestamp and clamps it to the track duration.
- `MusicHudPreview` renders title, artist, a one-second `NOW PLAYING` flash, progress and elapsed/remaining time.
- Music metadata is not written into the scooter's navigation text fields.
- No scooter buttons are remapped.

The missing `MusicState.playing()` helper was added. The Android build still needs a successful CI run before an APK can be called verified.

## Stronger TFT path found: NinebotEnhance

The maintained [NinebotEnhance](https://github.com/wx9614-cell/NinebotEnhance) source already has a dashboard music renderer:

- title and artist (ellipsized to fit);
- artwork or a music glyph;
- interpolated playback progress;
- elapsed and total time;
- a portrait/half-screen layout path that scales the 848×480 reference canvas into a 240×320 display.

The small-screen layout uses a single vertical card column. The music card is 84 reference pixels high. The existing code supports music as a widget, but its default auto-hide condition can make it disappear after a few seconds. The proposed patch below moves music to the bottom of the portrait column, keeps it visible while a track is active, and adds a one-second `NOW PLAYING` label after track changes. This leaves the upper display area available for the scooter's speed readout. The card will occupy part of the lower display area while music is active.

### Source patch prepared

`patches/NinebotEnhance-240x320-music-hud.patch` contains a proposed patch against the maintained NinebotEnhance source. It changes only dashboard drawing/layout behavior:

1. Track changes start a one-second banner timer.
2. The banner redraws smoothly and disappears after one second.
3. The title, artist and progress card remain visible while music is active on portrait displays.
4. The music card is placed at the bottom of the 240×320 single column.
5. It does not alter BLE vehicle settings or intercept scooter buttons.

This patch has not yet been applied to a NinebotEnhance checkout or built. It is source work, not a verified TFT APK.

## Rootless installation route: NPatch

The current NinebotEnhance module is built against libxposed API 101. NPatch's official documentation explicitly supports modern libxposed API 101/102 modules and runs without root. It offers an integrated mode that embeds the module inside a patched target app, so a separate manager does not need to stay running.

The planned rootless route is therefore:

1. Use the supported China Segway app package `cn.ninebot.ninebot`, preferably version 6.10.11 as a conservative target. NinebotEnhance lists 6.10.10–6.10.12 as supported; 6.10.12 has a protected business DEX and runtime-checked hooks.
2. Obtain the official target APK and the maintained NinebotEnhance module APK.
3. On Windows, use the official NPatch JAR in integrated mode to embed the module in the target app (NPatch documents the `--embed module.apk target.apk` workflow).
4. Install the patched China app only if its package is not already installed, configure the module, then pair/check compatibility without changing firmware or vehicle settings.

**Important signature/data warning:** NPatch re-signs the target app. Android will not install that patched APK over an existing app with the same package and a different signature. NPatch's official instructions require uninstalling the original target app first, which deletes that app's local data. The international Segway app uses a different package (`com.ninebot.segway`), so it is not the same package as the China app (`cn.ninebot.ninebot`); however, an already-installed China app would be at risk. Do not uninstall anything or install a patched APK until the package situation and account/pairing implications are checked.

NPatch documents Android 9+ and libxposed API 101/102 support. NinebotEnhance documents Android 11–16. That makes the S22's Android 16 version a plausible software target, but does not prove the complete combination works on this phone or scooter.

## F3 Pro compatibility is still the hardware blocker

- The F3 Pro has a 2.4-inch Smart TFT, but that does not establish its exact dashboard protocol.
- The archived NinebotPlay branch explicitly reports a 240×320 Bluetooth MPEG2 dashboard tested on an F2z.
- The maintained NinebotEnhance branch still marks the same 240×320 Bluetooth MPEG2 profile as awaiting hardware verification.
- The maintained branch has a 240×320/portrait rendering path, but the F3 Pro transport has not been verified.
- The maintained module's documented write surface is limited to navigation display data (instrument command 113) and day/night theme. No vehicle settings are intentionally changed.

## Acceptance criteria before calling this a working TFT prototype

- Confirm the F3 Pro display profile and transport without experimental vehicle-setting writes.
- Confirm the supported China app version and NPatch loading on Android 16.
- Confirm the renderer receives Spotify / YouTube Music sessions and draws on the F3 Pro TFT.
- Verify title/artist, one-second track-change banner and progress synchronization.
- Verify navigation, speed, battery and all normal scooter buttons remain unchanged.
- Only then prepare a user-installable APK. Until then, the phone preview and source patch are prototypes, not proof of working F3 Pro TFT projection.
