# Music HUD: phone prototype and F3 Pro TFT integration

## Verified phone-side prototype

The Android bridge in this repository compiles successfully and has been tested by the user on a Samsung S22:

- Spotify / YouTube Music session detection.
- Song title and artist.
- Live progress bar.
- One-second `NOW PLAYING` flash after a track change.
- No music metadata is written into scooter navigation text fields.
- No scooter buttons are remapped.

This proves the phone-side media-session reader and preview. It does not prove TFT output.

## TFT renderer patch: compiled module builds

The maintained [NinebotEnhance](https://github.com/wx9614-cell/NinebotEnhance) source already has a music renderer with artwork, title, artist, interpolated progress, elapsed time and total duration.

The F3 portrait HUD changes are applied by the guarded script `scripts/apply_ninebotenhance_music_hud.py`. It makes seven exact, single-occurrence source edits and fails closed if upstream code differs:

1. Start a monotonic one-second timer on a newly observed track.
2. Redraw during the banner interval and show `NOW PLAYING`.
3. Keep the music card visible while media is active on portrait / half-screen frames.
4. Place the music card at the bottom of the single-column layout, leaving the upper display area available.
5. Do not change BLE vehicle settings or button mappings.

GitHub Actions successfully compiled the patched NinebotEnhance Android module. The build produced two debug variants:

- `ninebotenhance-china-debug.apk` — module scope `cn.ninebot.ninebot`.
- `ninebotenhance-global-debug.apk` — experimental module scope `com.ninebot.segway`.

The global variant only changes the target package and Xposed scope. Its hook targets have not been verified against the international app. The China variant's maintained source lists 6.10.10, 6.10.11 and 6.10.12 as verified versions; newer builds are runtime-checked but not hand-verified.

**These APKs are Xposed modules, not standalone apps. Do not tap Install on them as if they were G3 Connect.** They must be embedded into the matching host app using NPatch Integrated mode.

## Rootless NPatch route and risks

Official NPatch documentation supports libxposed API 101/102 modules and the integrated command form:

```text
java -jar jar-v1.1.0-857-release.jar --embed module.apk target.apk
```

NPatch re-signs the host app. Android will not install the patched app over the original app with the same package and a different signature; NPatch's documentation says the original must be uninstalled first, which deletes that app's local data. Do not uninstall or patch the user's existing Segway app without a backup and explicit approval.

NinebotEnhance also ships an **Official compatibility mode** that is enabled by default. While enabled, it deliberately disables all host-app hooks. Turning it off enables the HUD hooks, but the project's own documentation warns that the official app may reject the connection when hooks are active. This needs careful validation before the user installs or relies on it.

The international Segway app package is `com.ninebot.segway`; the China app package is `cn.ninebot.ninebot`. The official support guidance distinguishes global and Chinese app variants, so the correct host app must match the scooter's region. Do not assume the China app is suitable for an EU scooter.

## F3 Pro compatibility is still unverified

- The F3 Pro has a 2.4-inch Smart TFT, but that does not establish its exact display transport or frame profile.
- The archived NinebotPlay project reports a 240×320 Bluetooth MPEG2 profile tested on an F2z.
- The maintained NinebotEnhance source has a 240×320 portrait layout path, but marks that profile as awaiting hardware verification.
- No successful screen render has yet been observed on an F3 Pro.

The patch itself only changes HUD drawing and layout. The wider NinebotEnhance module can also hook other app functions; keep its optional controls and vehicle-related features disabled during any future test. Its documented vehicle writes are navigation display data and day/night theme, so do not enable or test those features as part of the music HUD work.

## What remains before a real TFT prototype

1. Confirm whether the user's installed Segway app is global or China and whether a compatible host app can be used without risking existing app data.
2. Validate NPatch loading and the module's compatibility mode on Android 16.
3. Verify that the F3 Pro accepts the 240×320 display stream; the F2z result is not proof.
4. Verify title/artist, the one-second banner and progress on the actual TFT.
5. Confirm normal speed, battery, navigation, turn signals and mode button remain unaffected.

Until those checks pass, the compiled module is a real software build, but not a verified F3 Pro TFT installation.
