#!/usr/bin/env python3
"""
disasm.py  --  Disassembler da ISA implícita do Sprint (Google CTF 2020).

Ideia central
-------------
O laço principal do binário faz, a cada passo:

    sprintf(OUT, *PC, "", 0, &PC, OUT, <registradores...>)

onde `*PC` é a format string apontada pelo "program counter". O truque é que
`sprintf` conta os caracteres que gera, e essa contagem é gravada de volta na
memória com `%N$hn` (escrita de 16 bits). Assim:

  * `%1$00038s`  -> soma 38 ao comprimento (arg1 = string vazia "", só padding)
  * `%1$*8$s`    -> soma o VALOR do registrador ligado ao arg 8 (largura variável)
  * `%1$5s`      -> soma 5
  * `%c`         -> soma 1
  * `%4$s`       -> soma o comprimento do próprio buffer OUT (leitura do buffer de
                    saída do sprintf; comportamento indefinido, mas determinístico
                    na glibc alvo) -> usado em desvios condicionais
  * `%N$hn`      -> grava o comprimento ACUMULADO ATÉ AQUI (mod 2^16) no destino N

Portanto, percorrendo a format string da esquerda para a direita e mantendo o
comprimento acumulado de forma simbólica (constante + combinação de registradores,
tudo mod 65536), cada `%N$hn` vira uma atribuição. É exatamente essa "elevação"
(lifting) da semântica de biblioteca para uma ISA legível que este módulo faz.

Mapa de argumentos -> registradores
-----------------------------------
Derivado estaticamente da sequência de `push` que monta a chamada a sprintf em
main() (ver docs/writeup/01-p1-extracao-disassembly.md). Cada slot de memória é
alcançável por dois índices de argumento consecutivos: um como VALOR (para largura
variável `%*N$s`) e outro como PONTEIRO (para escrita `%N$hn`).

    arg 3  -> PC   (ponteiro para o program counter; toda instrução escreve nele)
    arg 4  -> OUT  (ponteiro para o buffer de saída; lido via %4$s nos desvios)
    arg >=5: reg(arg) = (arg - 3) // 2   ->  r1, r2, ...

Este mapa é uma HIPÓTESE de análise estática; o emulador (P3) confirma os valores
em tempo de execução comparando com o binário original.

Uso:
    python3 disasm.py ../out/M.bin --json ../out/sprint.json --txt ../out/sprint.asm
"""
import argparse
import json
import re

MOD = 1 << 16  # %hn escreve 16 bits

# diretiva: %ARG$... com variações de largura imediata, largura variável, hn, c, s
_DIR = re.compile(rb"%(\d+)\$(?:(\d+)s|\*(\d+)\$s|(hn)|(c)|(s))")


def reg_name(arg: int) -> str:
    """Traduz um índice de argumento de sprintf no nome do registrador/papel."""
    if arg == 3:
        return "PC"
    if arg == 4:
        return "OUT"
    return f"r{(arg - 3) // 2}"


class SymVal:
    """Valor simbólico mod 2^16: constante + soma de termos de registradores/OUT."""

    def __init__(self):
        self.const = 0
        self.terms = {}  # nome do reg -> coeficiente

    def add_const(self, k: int):
        self.const = (self.const + k) % MOD

    def add_reg(self, name: str, coeff: int = 1):
        self.terms[name] = self.terms.get(name, 0) + coeff
        if self.terms[name] == 0:
            del self.terms[name]

    def snapshot(self):
        s = SymVal()
        s.const = self.const
        s.terms = dict(self.terms)
        return s

    def __str__(self):
        parts = []
        for name, c in self.terms.items():
            if c == 1:
                parts.append(name)
            else:
                parts.append(f"{c}*{name}")
        if self.const or not parts:
            parts.append(str(self.const))
        return " + ".join(parts)

    def to_dict(self):
        return {"const": self.const, "terms": self.terms}


def split_instructions(table: bytes):
    """Recorta a tabela em instruções. Cada instrução é uma format string
    terminada em NUL. A região de dados/labirinto (tudo NUL) é ignorada."""
    insns = []
    i = 0
    n = len(table)
    while i < n:
        j = table.index(b"\x00", i) if b"\x00" in table[i:] else n
        cell = table[i:j]
        if cell:
            insns.append((i, cell))
        i = j + 1
    return insns


def decode_one(offset: int, fmt: bytes) -> dict:
    """Decodifica uma format string em uma instrução estruturada."""
    acc = SymVal()
    assigns = []       # (destino, valor_simbolico_no_momento)
    reads = []         # registradores lidos como largura variável
    reads_out = False  # leu o buffer OUT (%4$s)
    n_chars = 0        # nº de %c literais

    for m in _DIR.finditer(fmt):
        arg = int(m.group(1))
        imm_w, var_w, is_hn, is_c, is_s = m.group(2, 3, 4, 5, 6)
        if imm_w is not None:                      # %arg$<width>s  (largura imediata)
            acc.add_const(int(imm_w))
        elif var_w is not None:                    # %arg$*V$s      (largura variável)
            src = reg_name(int(var_w))
            acc.add_reg(src)
            reads.append(src)
        elif is_hn is not None:                    # %arg$hn        (escrita)
            assigns.append((reg_name(arg), acc.snapshot()))
        elif is_c is not None:                     # %arg$c
            acc.add_const(1)
            n_chars += 1
        elif is_s is not None:                     # %arg$s (tipicamente %4$s = OUT)
            if arg == 4:
                acc.add_reg("OUT")
                reads_out = True
            else:
                # %arg$s de outro argumento: string curta usada como incremento
                acc.add_reg(reg_name(arg))

    # classificação do opcode
    targets = [d for d, _ in assigns]
    non_pc = [d for d in targets if d != "PC"]
    if reads_out:
        kind = "BR"      # desvio condicional: consulta o buffer de saída
    elif non_pc and reads:
        kind = "ALU"     # r = combinação de registradores/imediatos
    elif non_pc:
        kind = "MOV"     # r = imediato
    else:
        kind = "JMP"     # apenas atualiza PC (fluxo sequencial/salto)

    # texto legível
    lines = []
    for dst, val in assigns:
        lines.append(f"{dst} = {val}")
    text = "; ".join(lines) if lines else "(nop)"

    return {
        "offset": offset,
        "raw": fmt.decode("latin-1"),
        "kind": kind,
        "assigns": [{"dst": d, "value": v.to_dict(), "value_str": str(v)} for d, v in assigns],
        "reads": reads,
        "reads_out": reads_out,
        "text": text,
    }


def disassemble(table: bytes):
    return [decode_one(off, fmt) for off, fmt in split_instructions(table)]


def render_txt(program) -> str:
    out = []
    out.append("; Sprint (Google CTF 2020) - disassembly da ISA implementada em sprintf")
    out.append("; PC/OUT = program counter / buffer de saida; r1.. = registradores")
    out.append("; valores sao mod 2^16 (escrita via %hn de 16 bits)")
    out.append(";")
    out.append(f"; {'offset':>8}  {'kind':<4}  instrucao")
    out.append(";" + "-" * 60)
    for ins in program:
        out.append(f"{ins['offset']:#08x}  {ins['kind']:<4}  {ins['text']}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Disassembler da ISA do Sprint")
    ap.add_argument("table", help="arquivo com os bytes da tabela M (de extract.py)")
    ap.add_argument("--json", default="sprint.json", help="saida estruturada em JSON")
    ap.add_argument("--txt", default="sprint.asm", help="saida legivel (disassembly)")
    args = ap.parse_args(argv)

    table = open(args.table, "rb").read()
    program = disassemble(table)

    with open(args.json, "w") as f:
        json.dump(program, f, ensure_ascii=False, indent=2)
    with open(args.txt, "w") as f:
        f.write(render_txt(program))

    # resumo por classe de opcode
    from collections import Counter
    hist = Counter(i["kind"] for i in program)
    print(f"{len(program)} instrucoes decodificadas")
    print("por classe:", dict(hist))
    print(f"JSON  -> {args.json}")
    print(f"ASM   -> {args.txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
