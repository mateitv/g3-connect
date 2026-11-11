package de.g3connect.maps;

/** Pure playback-position math shared by the live HUD and its tests. */
final class MusicProgress {
    static boolean moving(int state) { return state == 3 || state == 4 || state == 5; }

    static long position(long position, long duration, int state, float speed, long updatedAt, long now) {
        if (position < 0) return -1;
        double value = position;
        if (moving(state) && Float.isFinite(speed) && updatedAt > 0 && now > updatedAt) {
            value += (now - updatedAt) * (double) speed;
        }
        long result = (long) Math.max(0, Math.min(Long.MAX_VALUE, value));
        return duration > 0 ? Math.min(duration, result) : result;
    }

    static float fraction(long position, long duration) {
        if (position < 0 || duration <= 0) return 0f;
        return Math.max(0f, Math.min(1f, position / (float) duration));
    }

    static String time(long millis) {
        if (millis < 0) return "--:--";
        long seconds = millis / 1000;
        return (seconds / 60) + ":" + (seconds % 60 < 10 ? "0" : "") + (seconds % 60);
    }

    private MusicProgress() {}
}
