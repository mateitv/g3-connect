import importlib.util
from pathlib import Path
import sys
import unittest

MODULE = Path(__file__).parents[1] / "tools" / "f3_ble_frame_inspector.py"
SPEC = importlib.util.spec_from_file_location("f3_ble_frame_inspector", MODULE)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

class FrameInspectorTests(unittest.TestCase):
    def test_decodes_plaintext_frame_with_16bit_complement_checksum(self):
        body = bytes([0x5A, 0xA5, 0x02, 0x04, 0x01, 0x01, 0x10, 0x41, 0x42])
        check = (0xFFFF - (sum(body[2:]) & 0xFFFF)) & 0xFFFF
        packet = body + bytes([check & 0xFF, check >> 8])
        frames = mod.parse_frames(packet)
        self.assertEqual(len(frames), 1)
        frame = frames[0]
        self.assertEqual((frame.source, frame.destination), (0x04, 0x01))
        self.assertEqual((frame.command, frame.argument), (0x01, 0x10))
        self.assertEqual(frame.payload, b"AB")
        self.assertTrue(frame.checksum_status.startswith("MATCH"))

    def test_does_not_decode_unframed_data(self):
        self.assertEqual(mod.parse_frames(bytes([1, 2, 3])), [])

if __name__ == "__main__":
    unittest.main()
