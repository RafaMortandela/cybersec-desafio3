#!/usr/bin/env python3
"""P2: saída JSON do P1 -> IR nomeada, pseudocódigo e Python estruturado.

Decodifica raw em vez de reutilizar o mapa genérico de P1: arg5 é *dptr,
arg6 escreve *dptr e arg7 escreve dptr. Recupera JNZ de baixo byte.
O programa estruturado usa um perfil manual auditado do Sprint original;
não se apresenta como um decompilador geral nem como o emulador P3.
"""

import argparse
import hashlib
import json
import pprint
import re
from collections import Counter
from pathlib import Path

from extract import Elf64, find_table
from disasm import split_instructions

PROFILE_SHA256 = "925510065b1cd97c53bb6f46b64fbf9fe5a039aa892d6f5609e200e2c74d726a"
HALT = 0xFFFE
PHASES = (
    (0x0000, "crivo"), (0x0374, "comprimento"),
    (0x0536, "labirinto"), (0x0E60, "decifracao"), (0x13D9, "falha"),
)
DIRECTIVE = re.compile(r"%(\d+)\$(?:(\d+)s|\*(\d+)\$s|(hn)|(c)|(s))")
BRANCH = re.compile(r"%(\d+)\$c%1\$(\d+)s%2\$c%4\$s%1\$(\d+)s%3\$hn")


def source(arg: int) -> str:
    if arg == 5:
        return "load16(memory, dptr)"
    if arg == 6:
        return "dptr"
    if 8 <= arg <= 22 and arg % 2 == 0:
        return f"r{(arg - 8) // 2}"
    raise ValueError(f"argumento de leitura não suportado: {arg}")


def destination(arg: int) -> str:
    if arg == 3:
        return "PC"
    if arg == 6:
        return "store16(memory, dptr)"
    if arg == 7:
        return "dptr"
    if 9 <= arg <= 23 and arg % 2 == 1:
        return f"r{(arg - 9) // 2}"
    raise ValueError(f"argumento de escrita não suportado: {arg}")


def phase(offset: int) -> str:
    return next(name for start, name in reversed(PHASES) if offset >= start)


def lift_one(offset: int, raw: str) -> dict:
    branch = BRANCH.fullmatch(raw)
    base = {"offset": offset, "phase": phase(offset), "raw": raw}
    if branch:
        reg, first, second = map(int, branch.groups())
        zero = (2 + first + second) & 0xFFFF
        nonzero = (zero + first + 1) & 0xFFFF
        return dict(base, op="JNZ8", condition=source(reg),
                    zero=zero, nonzero=nonzero, successors=[zero, nonzero])
    matches = list(DIRECTIVE.finditer(raw))
    if "".join(m.group(0) for m in matches) != raw:
        raise ValueError(f"diretiva ou texto não reconhecido em {offset:#x}")
    constant = 0
    terms = []
    writes = []
    for match in matches:
        arg = int(match.group(1))
        width, variable, hn, char, string = match.group(2, 3, 4, 5, 6)
        if width is not None and arg == 1:
            constant = (constant + int(width)) & 0xFFFF
        elif variable is not None and arg == 1:
            terms.append(source(int(variable)))
        elif hn:
            writes.append({"destination": destination(arg),
                           "constant": constant, "terms": list(terms)})
        else:
            raise ValueError(f"padrão fora do perfil em {offset:#x}: {match.group(0)}")
    if not writes or writes[0]["destination"] != "PC" or writes[0]["terms"]:
        raise ValueError(f"PC não constante em {offset:#x}")
    if len(writes) > 2:
        raise ValueError(f"múltiplas escritas fora do perfil em {offset:#x}")
    target = writes[0]["constant"]
    if len(writes) == 1:
        return dict(base, op="HALT" if target == HALT else "JMP",
                    successors=[target], next=target)
    assignment = writes[1]
    return dict(base, op="ASSIGN", assignment=assignment,
                successors=[target], next=target)


def lift_program(records: list, table: bytes) -> tuple:
    """Exige cobertura exata do código do ELF; ignora registros de dados P1."""
    expected = {off: raw.decode("latin-1") for off, raw in split_instructions(table)
                if off < 0x7000 and raw.startswith(b"%")}
    seen = set()
    program, ignored = [], []
    for record in records:
        off, raw = record["offset"], record["raw"]
        if off in seen:
            raise ValueError(f"offset duplicado: {off:#x}")
        seen.add(off)
        if off not in expected:
            actual = table[off:off + len(raw)] if 0 <= off < len(table) else b""
            if off < 0x7000 or actual != raw.encode("latin-1"):
                raise ValueError(f"registro estranho em {off:#x}")
            ignored.append(off)
            continue
        if raw != expected[off]:
            raise ValueError(f"raw diverge do ELF em {off:#x}")
        program.append(lift_one(off, raw))
    if seen.intersection(expected) != set(expected):
        raise ValueError("JSON P1 não cobre todas as instruções do ELF")
    program.sort(key=lambda item: item["offset"])
    for ins in program:
        if any(target not in expected and target != HALT for target in ins["successors"]):
            raise ValueError(f"salto fora do código em {ins['offset']:#x}")
    return program, ignored


def expression(assignment: dict) -> str:
    parts = list(assignment["terms"])
    constant = assignment["constant"]
    if constant or not parts:
        parts.append(str(constant if constant < 32768 else constant - 65536))
    return "(" + " + ".join(parts) + ") & 0xffff"


def render(program: list) -> str:
    lines = ["# P2 - pseudocódigo nomeado com labels (não é Python executável)",
             "# load16/store16: little-endian, inclusive endereços ímpares",
             "# JNZ8 testa apenas byte baixo; leituras usam estado anterior à chamada",
             "# r0..r7 mudam de papel entre fases; ver documento P2", ""]
    previous = None
    for ins in program:
        if ins["phase"] != previous:
            previous = ins["phase"]
            lines += ["", f"# Fase: {previous}"]
        label = f"L_{ins['offset']:04x}"
        if ins["op"] == "JNZ8":
            text = (f"if ({ins['condition']} & 0xff) != 0: goto L_{ins['nonzero']:04x}"
                    f"; else: goto L_{ins['zero']:04x}")
        elif ins["op"] == "ASSIGN":
            a = ins["assignment"]
            text = f"{a['destination']} <- {expression(a)}; goto L_{ins['next']:04x}"
        else:
            text = "halt" if ins["op"] == "HALT" else f"goto L_{ins['next']:04x}"
        lines.append(f"{label}: {text}")
    return "\n".join(lines) + "\n"


def build(p1_path: Path, binary: Path, output: Path) -> dict:
    data = binary.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != PROFILE_SHA256:
        raise ValueError("ELF diferente do perfil Sprint auditado; não gerar modelo silenciosamente")
    elf = Elf64(data)
    _, offset, size = find_table(elf)
    table = data[offset:offset + size]
    records = json.loads(p1_path.read_text(encoding="utf-8"))
    program, ignored = lift_program(records, table)
    output.mkdir(parents=True, exist_ok=True)
    report = {"binary_sha256": digest, "instructions": len(program),
              "ignored_data_offsets": ignored, "branch_semantics": "low_byte_nonzero",
              "structuring": "manual audited Sprint profile", "program": program}
    (output / "p2_ir.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "p2_pseudocode.txt").write_text(render(program), encoding="utf-8")
    # Constantes do programa recuperadas de suas instruções, não de gen_data.py.
    by_offset = {ins["offset"]: ins for ins in program}
    length = by_offset[0x04A1]["assignment"]["constant"]
    count = (-by_offset[0x0DCB]["assignment"]["constant"]) & 0xFFFF
    flag_length = (-by_offset[0x0EA5]["assignment"]["constant"]) & 0xFFFF
    encrypted_address = by_offset[0x1297]["assignment"]["constant"]
    encrypted = list(table[encrypted_address:encrypted_address + flag_length])
    preamble = (
        '#!/usr/bin/env python3\n"""P2 gerado por src/lift.py. Não editar; regenere."""\n'
        f"# ELF SHA256: {digest}\n"
        f"INPUT_LENGTH = {length}\nCHECKPOINT_COUNT = {count}\n"
        f"START = {table[0xF100]}\nMAZE = {pprint.pformat(tuple(table[0xF000:0xF100]), compact=True)}\n"
        f"ENCRYPTED_FLAG = {pprint.pformat(tuple(encrypted), compact=True)}\n"
        f"TARGET_TAIL = {pprint.pformat(tuple(table[0xF103:0xF103 + 255]), compact=True)}\n\n"
    )
    template = Path(__file__).with_name("p2_model.py").read_text(encoding="utf-8")
    template = template[template.index("import argparse"):]
    (output / "p2_program.py").write_text(preamble + template, encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("p1_json", type=Path)
    parser.add_argument("--binary", type=Path, default=Path("sprint"))
    parser.add_argument("--out-dir", type=Path, default=Path("out"))
    args = parser.parse_args()
    report = build(args.p1_json, args.binary, args.out_dir)
    print(f"{report['instructions']} instruções reais; dados ignorados: "
          + ", ".join(hex(off) for off in report["ignored_data_offsets"]))
    print("por classe:", dict(Counter(ins["op"] for ins in report["program"])))
    print(f"Pseudocódigo, IR e programa Python gerados em {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
