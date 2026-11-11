package de.g3connect.maps;
import android.media.session.MediaController;
import android.media.session.PlaybackState;
/** Current local Android media session; metadata never leaves the phone. */
final class MusicState {
 static volatile MediaController controller;
 static volatile String title="",artist="";
 static volatile int playbackState=PlaybackState.STATE_NONE;
 static void update(MediaController c,String t,String a){
  controller=c;title=t==null?"":t;artist=a==null?"":a;
  PlaybackState p=c.getPlaybackState();playbackState=p==null?PlaybackState.STATE_NONE:p.getState();
 }
 static void clear(){controller=null;title="";artist="";playbackState=PlaybackState.STATE_NONE;}
 static boolean playing(){return playbackState==PlaybackState.STATE_PLAYING;}
}
