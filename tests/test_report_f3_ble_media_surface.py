import importlib.util
from pathlib import Path
import sys
import unittest

MODULE = Path(__file__).parents[1] / "tools" / "report_f3_ble_media_surface.py"
SPEC = importlib.util.spec_from_file_location("report_f3_ble_media_surface", MODULE)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class MediaSurfaceInventoryTests(unittest.TestCase):
    def test_extracts_printable_strings_with_offsets(self):
        data = b"\\x00bts_media_play\\x00artist\\x00"
        found = mod.extract_strings(data, 5)
        self.assertIn((1, "bts_media_play"), found)
        self.assertIn((16, "artist"), found)

    def test_minimum_length_is_respected(self):
        self.assertEqual(mod.extract_strings(b"\\x00abc\\x00abcd\\x00", 4), [(5, "abcd")])


if __name__ == "__main__":
    unittest.main()
