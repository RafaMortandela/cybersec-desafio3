#!/usr/bin/env python3
"""P3: interpretador da ISA Sprint sem sprintf ou o modelo estruturado P2."""
import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from extract import Elf64, find_table

PROFILE = '925510065b1cd97c53bb6f46b64fbf9fe5a039aa892d6f5609e200e2c74d726a'
HALT = 0xfffe
DIRECTIVE = re.compile(r'%(\d+)\$(?:(\d+)s|\*(\d+)\$s|(hn))')
BRANCH = re.compile(r'%(\d+)\$c%1\$(\d+)s%2\$c%4\$s%1\$(\d+)s%3\$hn')
READS = (5, 6, *range(8, 23, 2))
WRITES = (3, 6, 7, *range(9, 24, 2))


def decode(raw):
    """Compila primitivas, sem reconhecer fases ou laços do programa."""
    branch = BRANCH.fullmatch(raw)
    if branch:
        arg, first, second = map(int, branch.groups())
        if arg not in READS:
            raise ValueError('argumento de branch desconhecido')
        zero = (2 + first + second) & 65535
        return ('branch', arg, zero, (zero + first + 1) & 65535)
    matches = list(DIRECTIVE.finditer(raw))
    if not matches or ''.join(m[0] for m in matches) != raw:
        raise ValueError('formato fora da ISA Sprint')
    ops = []
    for m in matches:
        arg = int(m[1])
        if m[2] is not None and arg == 1:
            ops.append(('constant', int(m[2])))
        elif m[3] is not None and arg == 1 and int(m[3]) in READS:
            ops.append(('width', int(m[3])))
        elif m[4] and arg in WRITES:
            ops.append(('write', arg))
        else:
            raise ValueError('argumento ou diretiva desconhecida')
    if ('write', 3) not in ops:
        raise ValueError('instrução sem escrita no PC')
    return ('linear', ops)


@dataclass(frozen=True)
class Result:
    status: int
    accepted: bool
    flag: str
    pc: int
    dptr: int
    registers: tuple
    instructions: int


class Machine:
    def __init__(self, table, data=b''):
        if len(table) > 65536:
            raise ValueError('tabela maior que o espaço endereçável')
        self.memory = bytearray(65537)  # word em 0xffff inclui 0x10000
        self.memory[:len(table)] = table
        token = re.split(rb'[ \t\n\r\v\f]', data.lstrip(b' \t\n\r\v\f'), 1)[0][:255]
        self.memory[0xe000:0xe000 + len(token) + 1] = token + b'\0'
        self.pc = self.dptr = self.executed = 0
        self.regs = [0] * 8
        self.cache = {}

    def load16(self, address):
        return self.memory[address] | self.memory[address + 1] << 8

    def store16(self, address, value):
        self.memory[address:address + 2] = (value & 65535).to_bytes(2, 'little')

    def step(self):
        if self.pc == HALT:
            raise RuntimeError('máquina já parada')
        end = self.memory.find(0, self.pc)
        if end == -1:
            raise ValueError('instrução sem terminador')
        raw = bytes(self.memory[self.pc:end]).decode('latin-1')
        if raw not in self.cache:
            self.cache[raw] = decode(raw)
        ins = self.cache[raw]
        # Argumentos de valor e ponteiros são avaliados antes da chamada.
        ptr, regs = self.dptr, tuple(self.regs)
        values = {5: self.load16(ptr), 6: ptr}
        values.update({8 + 2 * i: value for i, value in enumerate(regs)})
        if ins[0] == 'branch':
            _, arg, zero, nonzero = ins
            self.pc = nonzero if values[arg] & 255 else zero
        else:
            count = 0
            for op, arg in ins[1]:
                if op == 'constant':
                    count += arg
                elif op == 'width':
                    count += values[arg]
                else:
                    value = count & 65535
                    if arg == 3:
                        self.pc = value
                    elif arg == 6:
                        self.store16(ptr, value)
                    elif arg == 7:
                        self.dptr = value
                    else:
                        self.regs[(arg - 9) // 2] = value
        self.executed += 1

    def run(self, max_steps=100000, trace=None):
        while self.pc != HALT:
            if self.executed >= max_steps:
                raise RuntimeError(f'limite de {max_steps} instruções excedido em PC={self.pc:#x}')
            if trace:
                trace.write(json.dumps({'step': self.executed, 'pc': self.pc,
                                        'dptr': self.dptr, 'registers': self.regs}) + '\n')
            self.step()
        flag = bytes(self.memory[0xe800:]).split(b'\0', 1)[0].decode('latin-1')
        return Result(self.regs[7], self.regs[7] == 0, flag, self.pc,
                      self.dptr, tuple(self.regs), self.executed)


def load_table(binary):
    data = Path(binary).read_bytes()
    if hashlib.sha256(data).hexdigest() != PROFILE:
        raise ValueError('binário diferente do perfil Sprint auditado')
    _, offset, size = find_table(Elf64(data))
    return data[offset:offset + size]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=Path('sprint'))
    parser.add_argument('--input', type=Path)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--trace', type=Path, help='estados antes das instruções em JSONL')
    parser.add_argument('--max-steps', type=int, default=100000)
    args = parser.parse_args()
    try:
        machine = Machine(load_table(args.binary), args.input.read_bytes() if args.input else sys.stdin.buffer.read())
        if args.trace:
            with args.trace.open('w', encoding='utf-8') as trace:
                result = machine.run(args.max_steps, trace)
        else:
            result = machine.run(args.max_steps)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(2, f'Erro P3: {error}\n')
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    elif result.accepted:
        print('Flag: ' + result.flag)
    else:
        print(f'Entrada rejeitada pela VM P3 (status {result.status})')
    return 0 if result.accepted else 1


if __name__ == '__main__':
    raise SystemExit(main())
