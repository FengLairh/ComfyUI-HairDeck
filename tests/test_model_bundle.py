import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_model_bundle import write_bundle, verify_archive
from verify_model_bundle import safe_path, verify


class OfflineModelBundleTests(unittest.TestCase):
    def test_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.dat'
            source.write_bytes(b'known model bytes' * 100)
            checksum = hashlib.sha256(source.read_bytes()).hexdigest()
            with redirect_stdout(io.StringIO()):
                archive, manifest = write_bundle(root / 'models.zip', {'ckpt/test.dat': (source, checksum)},
                                                 kind='models', readme='fixture')
                verify_archive(archive, manifest)
                with zipfile.ZipFile(archive) as packed:
                    packed.extractall(root / 'unpacked')
                verify(root / 'unpacked/hairdeck')
            extracted = root / 'unpacked/hairdeck/ckpt/test.dat'
            extracted.write_bytes(b'x' * source.stat().st_size)
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                verify(root / 'unpacked/hairdeck')

    def test_rejects_wrong_official_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'weight.dat'
            source.write_bytes(b'corrupted weights')
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'released SHA-256'):
                write_bundle(root / 'models.zip', {'weight.dat': (source, '0' * 64)}, kind='models', readme='fixture')
            self.assertFalse((root / 'models.zip').exists())

    def test_manifest_paths_are_contained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for value in ['../secret', '/absolute', 'C:/absolute', 'x\\..\\secret']:
                with self.subTest(path=value), self.assertRaises(ValueError):
                    safe_path(root, value)


if __name__ == '__main__':
    unittest.main()
