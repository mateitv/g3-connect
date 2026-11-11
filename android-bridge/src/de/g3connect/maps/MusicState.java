package de.g3connect.maps;
import android.media.session.MediaController;
import android.media.session.PlaybackState;
import android.media.MediaMetadata;
import android.os.SystemClock;
/** Current local Android media session; metadata never leaves the phone. */
final class MusicState {
 static volatile MediaController controller;
 static volatile String title="",artist="";
 static volatile int playbackState=PlaybackState.STATE_NONE;
 static volatile long durationMs,positionMs,positionUpdatedAt;
 static volatile float playbackSpeed=1f;
 static void update(MediaController c,String t,String a){
  controller=c;title=t==null?"":t;artist=a==null?"":a;
  PlaybackState p=c.getPlaybackState();playbackState=p==null?PlaybackState.STATE_NONE:p.getState();
  MediaMetadata m=c.getMetadata();durationMs=m==null?0:Math.max(0,m.getLong(MediaMetadata.METADATA_KEY_DURATION));
  positionMs=p==null?-1:p.getPosition();positionUpdatedAt=p==null?0:p.getLastPositionUpdateTime();playbackSpeed=p==null?1f:p.getPlaybackSpeed();
 }
 static void clear(){controller=null;title="";artist="";playbackState=PlaybackState.STATE_NONE;durationMs=0;positionMs=-1;positionUpdatedAt=0;playbackSpeed=1f;}
 static long positionNow(){
  long position=positionMs;if(position<0)return -1;
  if(playing()&&positionUpdatedAt>0){long now=SystemClock.elapsedRealtime();if(now>positionUpdatedAt)position+=(long)((now-positionUpdatedAt)*Math.max(0f,playbackSpeed));}
  position=Math.max(0,position);return durationMs>0?Math.min(durationMs,position):position;
 }
 static String time(long millis){if(millis<0)return "--:--";long seconds=millis/1000;return (seconds/60)+":"+(seconds%60<10?"0":"")+(seconds%60);}
 static boolean playing(){return playbackState==PlaybackState.STATE_PLAYING;}
}
