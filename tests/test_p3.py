"""P3: primitivas, comparação com P2 e saída do ELF original."""
import importlib.util
import io
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from emulate import Machine, decode, load_table


class PrimitiveTests(unittest.TestCase):
    def machine(self, code):
        return Machine(code.encode() + b'\0')

    def test_modulo_and_memory_word(self):
        m = self.machine('%1$65534s%3$hn%1$65535s%9$hn')
        m.step()
        self.assertEqual(m.regs[0], 65533)
        m.store16(0xffff, 0x1234)
        self.assertEqual(m.load16(0xffff), 0x1234)
        m.store16(3, 0xabcd)
        self.assertEqual(bytes(m.memory[3:5]), b'\xcd\xab')

    def test_snapshot_register_and_pointer(self):
        m = self.machine('%1$65534s%3$hn%1$*8$s%9$hn%1$*8$s%11$hn%7$hn%6$hn')
        m.regs[0] = 3
        m.dptr = 0x8000
        m.step()
        self.assertEqual(m.regs[:2], [1, 4])
        self.assertEqual(m.dptr, 4)
        self.assertEqual(m.load16(0x8000), 4)

    def test_branch_low_byte(self):
        for value, expected in [(0, 0x180), (256, 0x180), (1, 0x324), (257, 0x324)]:
            m = self.machine('%8$c%1$419s%2$c%4$s%1$65499s%3$hn')
            m.regs[0] = value
            m.step()
            self.assertEqual(m.pc, expected)

    def test_unknown_format_and_limit(self):
        with self.assertRaises(ValueError):
            decode('%99$d')
        with self.assertRaises(RuntimeError):
            self.machine('%1$0s%3$hn').run(max_steps=3)

    def test_trace(self):
        trace = io.StringIO()
        self.machine('%1$65534s%3$hn').run(trace=trace)
        self.assertEqual(json.loads(trace.getvalue())['pc'], 0)


class ProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_table(ROOT / 'sprint')
        spec = importlib.util.spec_from_file_location('p2_for_p3', ROOT / 'out/p2_program.py')
        cls.p2 = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.p2
        spec.loader.exec_module(cls.p2)
        route = (ROOT / 'out/maze_path.txt').read_bytes().strip()
        cls.cases = [route, b'', route[:-1], route+b'r', b'r'*254,
                     b'x'*254, b'lr'*127, b'du'*127, b'\0'+route,
                     b' \n'+route+b' trailing', b'r'*256, b'\xff'*254]
        rng = random.Random(20261001)
        for _ in range(30):
            mutation = bytearray(route)
            mutation[rng.randrange(254)] = rng.choice(b'urdlx')
            cls.cases.append(bytes(mutation))
        cls.cases += [bytes(rng.choice(b'urdlx') for _ in range(254)) for _ in range(20)]

    def test_valid_route_and_sieve(self):
        machine = Machine(self.table, self.cases[0])
        result = machine.run()
        self.assertTrue(result.accepted)
        self.assertEqual(result.instructions, 19234)
        self.assertEqual(result.flag, 'CTF{n0w_ev3n_pr1n7f_1s_7ur1ng_c0mpl3te}')
        for n in range(256):
            prime = n >= 2 and all(n % d for d in range(2, n))
            self.assertEqual(machine.load16(0x7000+2*n), int(not prime))

    def test_differential_p2(self):
        statuses = set()
        for data in self.cases:
            with self.subTest(data=data[:12]):
                actual = Machine(self.table, data).run()
                expected = self.p2.run(data)
                self.assertEqual((actual.status, actual.accepted, actual.flag),
                                 (expected.status, expected.accepted, expected.flag))
                statuses.add(actual.status)
        self.assertEqual(statuses, set(range(6)))

    @unittest.skipUnless(platform.system() == 'Linux' and platform.machine() == 'x86_64'
                         and Path('/lib64/ld-linux-x86-64.so.2').exists(),
                         'ELF original requer Linux x86-64 e loader glibc')
    def test_differential_original_stdout(self):
        for data in self.cases:
            with self.subTest(data=data[:12]):
                result = Machine(self.table, data).run()
                proc = subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(ROOT/'sprint')],
                                      input=data, capture_output=True, timeout=10,
                                      env={**os.environ, 'LC_ALL': 'C'})
                self.assertEqual(proc.returncode, 0)
                expected = b'Input password:\n'
                if result.flag:
                    expected += ('Flag: '+result.flag+'\n').encode('latin-1')
                self.assertEqual(proc.stdout, expected)
                self.assertEqual(proc.stderr, b'')


if __name__ == '__main__':
    unittest.main()
