#!/usr/bin/env python3
"""Retarget a patched NinebotEnhance build to the international Segway Mobility app.

The upstream hook targets remain the Chinese app's cn.ninebot.* classes. This
variant only changes the host package scope to com.ninebot.segway; it is an
experimental compatibility build and must be runtime-verified before use.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
protocol = root / "app/src/main/java/dev/ichinomiya/ninebotenhance/ipc/Protocol.java"
scope = root / "app/src/main/resources/META-INF/xposed/scope.list"


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Refusing to retarget {path}: expected one exact match, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


replace_once(protocol, 'MODULE = "dev.ichinomiya.ninebotenhance", TARGET = "cn.ninebot.ninebot";',
             'MODULE = "dev.ichinomiya.ninebotenhance", TARGET = "com.ninebot.segway";')
replace_once(scope, "cn.ninebot.ninebot\n", "com.ninebot.segway\n")
print("Retargeted module scope to com.ninebot.segway. Hook compatibility remains unverified.")
