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
  return MusicProgress.position(positionMs,durationMs,playbackState,playbackSpeed,positionUpdatedAt,SystemClock.elapsedRealtime());
 }
 static String time(long millis){return MusicProgress.time(millis);}
 static void action(String action){
  MediaController current=controller;if(current==null)return;
  try{
   MediaController.TransportControls controls=current.getTransportControls();
   if("previous".equals(action))controls.skipToPrevious();
   else if("next".equals(action))controls.skipToNext();
   else if(playing())controls.pause();else controls.play();
  }catch(RuntimeException e){ConnectService.log("Mediensteuerung fehlgeschlagen: "+e.getClass().getSimpleName());}
 }

}
