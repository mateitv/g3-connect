#!/usr/bin/env python3
"""Apply the portrait music HUD changes to a clean NinebotEnhance checkout.

This deliberately performs exact, single-occurrence replacements. It fails closed
if upstream source has changed, rather than silently producing a partial patch.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
hud = root / "app/src/main/java/dev/ichinomiya/ninebotenhance/notification/DashboardHud.java"
sidebar = root / "app/src/main/java/dev/ichinomiya/ninebotenhance/core/SidebarLayout.java"


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Refusing to patch {path}: expected one exact match, found {count}: {old[:100]!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


replace_once(
    hud,
    'private final long[] shownUntil=new long[WidgetSettings.CONDITIONAL.length];private String musicKeyShown="";private boolean musicMovingShown;',
    'private final long[] shownUntil=new long[WidgetSettings.CONDITIONAL.length];private String musicKeyShown="";private boolean musicMovingShown;\n'
    '    /** Monotonic timestamp of the last newly observed track; used for the one-second toast. */\n'
    '    private long musicTrackChangedAt;'
)

replace_once(
    hud,
    'ride=null;Arrays.fill(shownUntil,0);musicKeyShown="";musicMovingShown=false;volumeSeq=-1;volumeShownAt=volumeShownUntil=-1;volumeFillAt=0;volumeFillFrom=volumeFillTo=0;revision++;',
    'ride=null;Arrays.fill(shownUntil,0);musicKeyShown="";musicMovingShown=false;musicTrackChangedAt=0;volumeSeq=-1;volumeShownAt=volumeShownUntil=-1;volumeFillAt=0;volumeFillFrom=volumeFillTo=0;revision++;'
)

replace_once(
    hud,
    '''        if(activeMusic(nextMusic)){
            String key=musicKey(nextMusic);boolean moving=MusicPlayback.moving(nextMusic.getInt("state"));
            int fired=(!musicActive()||!key.equals(musicKeyShown)?WidgetCondition.TRACK_CHANGE:0)|(!musicActive()||moving!=musicMovingShown?WidgetCondition.PLAYBACK_CHANGE:0);
            if(fired!=0)fire(fired,now);
            musicKeyShown=key;musicMovingShown=moving;
        }else musicKeyShown="";''',
    '''        if(activeMusic(nextMusic)){
            String key=musicKey(nextMusic);boolean moving=MusicPlayback.moving(nextMusic.getInt("state"));
            boolean trackChanged=!musicActive()||!key.equals(musicKeyShown);
            if(trackChanged)musicTrackChangedAt=now;
            int fired=(trackChanged?WidgetCondition.TRACK_CHANGE:0)|(!musicActive()||moving!=musicMovingShown?WidgetCondition.PLAYBACK_CHANGE:0);
            if(fired!=0)fire(fired,now);
            musicKeyShown=key;musicMovingShown=moving;
        }else{musicKeyShown="";musicTrackChangedAt=0;}'''
)

replace_once(
    hud,
    '        if(widgets.enabled(WidgetSettings.MUSIC)&&(musicActive()?conditionMet(WidgetSettings.MUSIC,now):widgets.condition(WidgetSettings.MUSIC).mode()==WidgetCondition.ALWAYS))mask|=WidgetSettings.MUSIC;',
    '''        // Keep active music visible on the portrait half-screen dashboard.
        if(widgets.enabled(WidgetSettings.MUSIC)&&(musicActive()&&(halfScreen||conditionMet(WidgetSettings.MUSIC,now))
                ||!musicActive()&&widgets.condition(WidgetSettings.MUSIC).mode()==WidgetCondition.ALWAYS))mask|=WidgetSettings.MUSIC;'''
)

replace_once(
    hud,
    '        long tick=animating(now)?now/50:musicMoving(now)||chartLive(now)||probeShown()?now/1000:0;',
    '''        boolean nowPlayingBanner=musicTrackChangedAt>0&&now>=musicTrackChangedAt&&now-musicTrackChangedAt<1000;
        long tick=animating(now)||nowPlayingBanner?now/50:musicMoving(now)||chartLive(now)||probeShown()?now/1000:0;'''
)

replace_once(
    hud,
    '        if(!idle)centerLine(c,fit(musicArtist(),labelsWidth,10,false),labelsLeft,headerCenter+9,10,p.label(),false);',
    '''        if(!idle)centerLine(c,fit(musicArtist(),labelsWidth,10,false),labelsLeft,headerCenter+9,10,p.label(),false);
        if(!idle&&musicTrackChangedAt>0&&now>=musicTrackChangedAt&&now-musicTrackChangedAt<1000){
            paint.setStyle(Paint.Style.FILL);paint.setTextSize(8);paint.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
            paint.setColor(p.accent());String notice="NOW PLAYING";c.drawText(notice,labelsLeft,11,paint);
        }'''
)

replace_once(
    sidebar,
    '        if(singleColumn){ArrayList<Integer> all=new ArrayList<>(right);all.addAll(left);right=all;left=List.of();dodge=false;occlusions=List.of();}',
    '''        if(singleColumn){
            ArrayList<Integer> all=new ArrayList<>(right);all.addAll(left);
            // The configured card order is bottom-up; put music at the bottom band.
            all.remove(Integer.valueOf(WidgetSettings.MUSIC));all.add(0,WidgetSettings.MUSIC);
            right=all;left=List.of();dodge=false;occlusions=List.of();
        }'''
)

print("Applied 7 guarded source edits to DashboardHud.java and SidebarLayout.java.")
