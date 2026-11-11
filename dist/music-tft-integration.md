# Music HUD: phone prototype and TFT integration path

## Current implementation

The Android bridge on `feature/music-hud-prototype` contains a phone-side 240×320 preview:

- Android media sessions are read locally by `MapsListener` (Spotify, YouTube Music, and other players that publish a media session).
- `MusicState` holds title, artist, duration, playback state, position and playback speed.
- `MusicProgress` interpolates position from Android's last position-update timestamp and clamps it to the track duration.
- `MusicHudPreview` renders title, artist, a one-second NOW PLAYING banner, progress and elapsed/remaining time.
- Music metadata is not written into the scooter's navigation text fields.
- No scooter buttons are remapped.

A missing `MusicState.playing()` helper used by the UI was added in the latest commit. The Android build still needs a successful CI run before an APK can be called verified.

## Why this app cannot draw the TFT music card directly

The G3 Connect BLE bridge currently uses the scooter's navigation display commands. Those commands carry navigation fields, not an arbitrary 240×320 bitmap or widget layout. Encoding song metadata into those fields was intentionally removed because it corrupts the normal navigation experience and does not create a real music HUD.

The more promising route is the existing NinebotEnhance dashboard renderer, which runs inside the official Ninebot app and uses its own dashboard projection path.

## TFT integration target

The existing NinebotEnhance / NinebotPlay code already has a music card renderer with title, artist, playback progress, elapsed/remaining time and artwork. The 240×320 small-screen renderer currently prioritizes speed plus battery/BMS rows. The proposed small-screen behavior is:

1. Keep the speed display at the top.
2. When a music session is active, draw the existing music card in the lower panel (about 84 px high).
3. On track change, show a short NOW PLAYING banner for approximately one second.
4. When no music is active, restore the existing battery/BMS rows.
5. Do not intercept turn indicators, mode or other scooter controls.

## Rootless Android route under investigation

The maintained NinebotEnhance source documents Android 11–16 and screen-casting/drawing modes that do not require root or Shizuku. Its module scope is the China Segway app package `cn.ninebot.ninebot`, with app versions 6.10.10–6.10.12. Its 240×320 Bluetooth MPEG2 profile is still marked as awaiting hardware verification.

NPatch is a rootless Xposed-compatible loader that supports modern libxposed modules. In principle it may allow the module to run in a patched copy of the China app on an unrooted Android 16 phone. This combination has not yet been built or tested with this specific NinebotEnhance release.

Important safety/compatibility constraints:

- Do not install an unknown repackaged Ninebot APK or the archived NPatch bundle blindly.
- Patching an app changes its signature; replacing an already installed app of the same package can require uninstalling it and may lose app data. The international app uses a different package, but China-app pairing/login behavior still needs verification.
- Do not change scooter firmware, region, speed limits or controller settings.
- The F2z 240×320 test report is not proof that the F3 Pro uses the same dashboard transport.
- The F3 Pro's 2.4-inch TFT size alone does not prove protocol compatibility.

## Acceptance criteria before calling it a working TFT prototype

- Confirm the exact F3 Pro display profile and transport without sending experimental writes.
- Confirm a supported China app build and rootless module loading on Android 16.
- Confirm the renderer receives the media session and draws on the F3 Pro TFT.
- Verify title/artist, one-second track-change banner and progress synchronization.
- Verify navigation, speed, battery and all normal scooter buttons remain unchanged.
- Only then prepare a user-installable APK; until then, the phone preview is the only verified visual prototype.
