"""P2: evidência estática e comparação com uma pequena referência da IR.

A referência abaixo é apenas um oráculo de teste. Não executa sprintf nem o
ELF e não substitui a validação diferencial externa de P3/P5/P6.
"""

import importlib.util
import json
import random
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lift import build, lift_one, lift_program  # noqa: E402
from solve_maze import decode_maze, load_table, solve  # noqa: E402


def reference_ir(program, table, data):
    memory = bytearray(65538)
    memory[:len(table)] = table
    token = re.split(rb"[ \t\n\r\v\f]", data.lstrip(b" \t\n\r\v\f"), 1)[0][:255]
    memory[0xE000:0xE000 + len(token) + 1] = token + b"\0"
    regs = {f"r{i}": 0 for i in range(8)}
    regs["dptr"] = 0
    instructions = {ins["offset"]: ins for ins in program}
    pc = 0
    for _ in range(100000):
        if pc == 0xFFFE:
            flag = bytes(memory[0xE800:]).split(b"\0", 1)[0].decode("latin-1")
            return regs["r7"], flag
        ins = instructions[pc]

        def read(name):
            if name.startswith("load16"):
                ptr = regs["dptr"]
                return memory[ptr] | memory[ptr + 1] << 8
            return regs[name]

        if ins["op"] == "JNZ8":
            pc = ins["nonzero"] if read(ins["condition"]) & 255 else ins["zero"]
        else:
            if ins["op"] == "ASSIGN":
                a = ins["assignment"]
                value = (a["constant"] + sum(read(term) for term in a["terms"])) & 65535
                dst = a["destination"]
                if dst.startswith("store16"):
                    ptr = regs["dptr"]
                    memory[ptr:ptr + 2] = value.to_bytes(2, "little")
                else:
                    regs[dst] = value
            pc = ins["next"]
    raise AssertionError("limite de execução da referência excedido")


class LiftingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name)
        cls.report = build(ROOT / "out/sprint.json", ROOT / "sprint", cls.output)
        cls.table = load_table(ROOT / "sprint")
        spec = importlib.util.spec_from_file_location("p2_generated_test", cls.output / "p2_program.py")
        cls.model = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.model
        spec.loader.exec_module(cls.model)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_instruction_coverage_and_data(self):
        self.assertEqual(self.report["instructions"], 146)
        self.assertEqual(self.report["ignored_data_offsets"], [0xF000, 0xF102])
        self.assertEqual(sum(i["op"] == "JNZ8" for i in self.report["program"]), 21)

    def test_dereference_and_branch_targets(self):
        p = {i["offset"]: i for i in self.report["program"]}
        self.assertEqual(p[0x004A]["assignment"]["destination"], "store16(memory, dptr)")
        self.assertEqual(p[0x0026]["assignment"]["destination"], "dptr")
        self.assertEqual((p[0x015B]["zero"], p[0x015B]["nonzero"]), (0x0180, 0x0324))
        # 0x100 é zero para JNZ8, embora seja diferente de zero em 16 bits.
        self.assertEqual((p[0x034F]["zero"], p[0x034F]["nonzero"]), (0x0374, 0x00DA))

    def test_rejects_unknown_directives_and_missing_or_modified_code(self):
        with self.assertRaises(ValueError):
            lift_one(0, "%1$00038s%3$hn%99$d")
        records = json.loads((ROOT / "out/sprint.json").read_text())
        with self.assertRaises(ValueError):
            lift_program(records[1:], self.table)
        records[0]["raw"] += "A"
        with self.assertRaises(ValueError):
            lift_program(records, self.table)

    def test_rejects_other_binary_profile(self):
        wrong = self.output / "other.elf"
        wrong.write_bytes((ROOT / "sprint").read_bytes() + b"x")
        with self.assertRaises(ValueError):
            build(ROOT / "out/sprint.json", wrong, self.output)

    def test_sieve_against_trial_division(self):
        mask = self.model.sieve_nonprime()
        for n in range(256):
            prime = n >= 2 and all(n % divisor for divisor in range(2, n))
            self.assertEqual(mask[n] == 0, prime, n)

    def test_valid_route_and_decryption(self):
        route = solve(decode_maze(self.table)).encode("ascii")
        result = self.model.run(route + b"\n")
        self.assertTrue(result.accepted)
        self.assertEqual((result.steps, result.checkpoints, result.position), (254, 9, 0x1F))
        self.assertEqual(result.flag, "CTF{n0w_ev3n_pr1n7f_1s_7ur1ng_c0mpl3te}")
        self.assertEqual((result.status, result.flag), reference_ir(self.report["program"], self.table, route))

    def test_all_failure_statuses(self):
        route = (ROOT / "out/maze_path.txt").read_bytes().strip()
        cases = [(b"", 5), (b"r" * 254, 4), (b"x" * 254, 1),
                 (b"lr" * 127, 2), (b"du" * 127, 3), (route[:-1], 5)]
        for data, expected in cases:
            with self.subTest(expected=expected):
                result = self.model.run(data)
                self.assertEqual(result.status, expected)
                self.assertFalse(result.accepted)

    def test_structured_model_matches_ir_for_varied_inputs(self):
        route = (ROOT / "out/maze_path.txt").read_bytes().strip()
        cases = [route, b" \n" + route + b" trailing", route + b"r",
                 b"r" * 256, b"x" * 254, b"ur" * 127, b"rl" * 127,
                 b"u" * 254, b"\0" + route]
        rng = random.Random(20261001)
        for _ in range(30):
            mutated = bytearray(route)
            mutated[rng.randrange(254)] = rng.choice(b"urdlx")
            cases.append(bytes(mutated))
        cases += [bytes(rng.choice(b"urdlx") for _ in range(254)) for _ in range(20)]
        for data in cases:
            with self.subTest(data=data[:16]):
                result = self.model.run(data)
                self.assertEqual((result.status, result.flag),
                                 reference_ir(self.report["program"], self.table, data))


if __name__ == "__main__":
    unittest.main()
