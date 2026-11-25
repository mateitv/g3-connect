#!/usr/bin/env python3
"""Retarget a patched NinebotEnhance build to the international Segway Mobility app.

This changes both the module scope and the compatibility-provider caller check.
The upstream hook targets still need runtime verification against the installed
international app version before this build is safe to use.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
protocol = root / "app/src/main/java/dev/ichinomiya/ninebotenhance/ipc/Protocol.java"
scope = root / "app/src/main/resources/META-INF/xposed/scope.list"
provider = root / "app/src/main/java/dev/ichinomiya/ninebotenhance/service/CompatibilityProvider.java"


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Refusing to retarget {path}: expected one exact match, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


replace_once(protocol, 'MODULE = "dev.ichinomiya.ninebotenhance", TARGET = "cn.ninebot.ninebot";',
             'MODULE = "dev.ichinomiya.ninebotenhance", TARGET = "com.ninebot.segway";')
replace_once(scope, "cn.ninebot.ninebot\n", "com.ninebot.segway\n")
replace_once(
    provider,
    "import dev.ichinomiya.ninebotenhance.hook.OfficialCompatibility;\n",
    "import dev.ichinomiya.ninebotenhance.hook.OfficialCompatibility;\n"
    "import dev.ichinomiya.ninebotenhance.ipc.Protocol;\n",
)
replace_once(
    provider,
    'target |= "cn.ninebot.ninebot".equals(name);',
    "target |= Protocol.TARGET.equals(name);",
)
print("Retargeted module scope and provider caller check to com.ninebot.segway.")
print("Hook compatibility with the installed Segway Mobility version remains unverified.")
