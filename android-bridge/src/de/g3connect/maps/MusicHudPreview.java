package de.g3connect.maps;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.os.SystemClock;
import android.view.View;

/**
 * Phone-side 240x320 preview of the intended TFT music HUD.
 * This is deliberately a preview only: it does not write fake music data into
 * the scooter's navigation fields or claim that the TFT accepts arbitrary graphics.
 */
final class MusicHudPreview extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF box = new RectF();
    private String previousTrack = "";
    private long trackChangedAt;

    MusicHudPreview(Context context) {
        super(context);
        setLayerType(View.LAYER_TYPE_SOFTWARE, null);
        setMinimumHeight(480);
    }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float sx = getWidth() / 240f;
        float sy = getHeight() / 320f;
        canvas.save();
        canvas.scale(sx, sy);
        final long now = SystemClock.elapsedRealtime();
        final String title = clean(MusicState.title);
        final String artist = clean(MusicState.artist);
        final String key = title + "\u0000" + artist;
        if (!key.equals(previousTrack)) {
            previousTrack = key;
            trackChangedAt = now;
        }

        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0xFF080D13);
        canvas.drawRect(0, 0, 240, 320, paint);

        paint.setColor(0xFF18232F);
        canvas.drawRect(0, 0, 240, 38, paint);
        paint.setColor(0xFF73E0CF);
        paint.setTextSize(11);
        paint.setTypeface(android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.BOLD));
        canvas.drawText("G3 CONNECT  /  MUSIC", 14, 24, paint);
        paint.setColor(0xFF91A3B6);
        paint.setTextSize(9);
        canvas.drawText(MusicState.playing() ? "PLAYING" : MusicState.controller == null ? "NO MEDIA SESSION" : "PAUSED", 14, 56, paint);

        if (!title.isEmpty() && now - trackChangedAt < 1000) {
            box.set(135, 44, 226, 65);
            paint.setColor(0xFF174A43);
            canvas.drawRoundRect(box, 8, 8, paint);
            paint.setColor(0xFFB9FFF1);
            paint.setTextSize(8);
            paint.setTypeface(android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.BOLD));
            canvas.drawText("NOW PLAYING", 145, 58, paint);
        }

        paint.setColor(0xFFFFFFFF);
        paint.setTextSize(18);
        paint.setTypeface(android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.BOLD));
        drawFitted(canvas, title.isEmpty() ? "No song playing" : title, 14, 126, 212);
        paint.setColor(0xFF9BAFC2);
        paint.setTextSize(13);
        paint.setTypeface(android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.NORMAL));
        drawFitted(canvas, artist.isEmpty() ? "Open Spotify or YouTube Music" : artist, 14, 153, 212);

        paint.setColor(0xFF263442);
        box.set(14, 220, 226, 228);
        canvas.drawRoundRect(box, 4, 4, paint);
        long duration = MusicState.durationMs;
        long position = MusicState.positionNow();
        float progress = MusicProgress.fraction(position, duration);
        if (progress > 0) {
            paint.setColor(0xFF4ED6C2);
            box.set(14, 220, 14 + 212 * progress, 228);
            canvas.drawRoundRect(box, 4, 4, paint);
        }

        paint.setColor(0xFFB6C5D3);
        paint.setTextSize(10);
        paint.setTypeface(android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.NORMAL));
        canvas.drawText(MusicState.time(position), 14, 249, paint);
        String remaining = duration > 0 ? MusicState.time(Math.max(0, duration - Math.max(0, position))) : "--:--";
        float width = paint.measureText(remaining);
        canvas.drawText(remaining, 226 - width, 249, paint);

        paint.setColor(0xFF263442);
        canvas.drawRect(14, 280, 226, 281, paint);
        paint.setColor(0xFF617487);
        paint.setTextSize(9);
        canvas.drawText("DISPLAY LAYOUT PREVIEW  ·  240 × 320", 14, 300, paint);
        canvas.restore();

        if (isShown()) postInvalidateDelayed(180);
    }

    private void drawFitted(Canvas canvas, String value, float x, float y, float maxWidth) {
        String text = value;
        if (paint.measureText(text) > maxWidth) {
            while (text.length() > 1 && paint.measureText(text + "…") > maxWidth) {
                text = text.substring(0, text.length() - 1);
            }
            text += "…";
        }
        canvas.drawText(text, x, y, paint);
    }

    private static String clean(String value) {
        return value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').trim();
    }
}
