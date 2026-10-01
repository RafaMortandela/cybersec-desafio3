"""P5: o script de validação roda sem o ELF e aprova P3 x P2."""
import subprocess
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


class ValidateTests(unittest.TestCase):
    def test_emulator_only(self):
        proc = subprocess.run([sys.executable, str(ROOT / 'src/validate.py'), '--emulator-only'],
                              capture_output=True, text=True, encoding='utf-8', timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('status vistos: [0, 1, 2, 3, 4, 5]', proc.stdout)


if __name__ == '__main__':
    unittest.main()
