#!/usr/bin/env python3
"""P5: validação ponta a ponta e testes diferenciais da solução Sprint.

1. E2E: regenera a senha com o solver P4, executa o ELF original e confere a flag.
2. Diferencial: para entradas válidas, inválidas e parciais compara
   - stdout do ELF original  x  stdout esperado a partir do emulador P3;
   - estado final (status, aceitação, flag) do emulador P3  x  modelo P2.
O ELF só expõe stdout (o estado interno vive em memória `sprintf`), então a
comparação com o binário é feita pela saída; o estado completo é comparado
entre P3 e P2.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from emulate import PROFILE, Machine, load_table  # noqa: E402
from solve_maze import decode_maze, solve, trace  # noqa: E402
from solve_maze import load_table as maze_table  # noqa: E402

LOADER = '/lib64/ld-linux-x86-64.so.2'
PROMPT = b'Input password:\n'
FLAG_RE = b'Flag: CTF{'
TIMEOUT = 10


class Backend:
    """Executa o ELF original com stdin controlado e devolve (rc, stdout, stderr)."""

    def __init__(self, name, binary, image=None, image_binary=None, image_loader=LOADER):
        self.name, self.binary, self.image = name, Path(binary).resolve(), image
        # image_binary: caminho do ELF dentro da imagem. Quando definido, nao ha
        # bind mount; o binario ja vem assado (ver docker/Dockerfile). Isso
        # evita o bloqueio de SELinux em hosts Fedora/RHEL, que faria o ELF
        # falhar com rc=127 em toda a matriz por um motivo que nao e a libc.
        self.image_binary = image_binary
        # image_loader: 'none' executa /sprint diretamente, deixando o kernel
        # resolver o PT_INTERP do proprio ELF. E o teste correto sob musl, onde
        # nao existe loader da glibc para invocar. Nos demais casos usamos a
        # loader da glibc explicitamente, porque o arquivo do repositorio pode
        # nao ter bit de execucao.
        self.image_loader = image_loader

    def _cmd(self, *tail):
        if self.name == 'native':
            return [LOADER, str(self.binary), *tail]
        remote = self.image_binary or '/sprint'
        cmd = ['docker', 'run', '--rm', '-i', '--platform', 'linux/amd64',
               '-e', 'LC_ALL=C']
        if not self.image_binary:
            cmd += ['-v', f'{self.binary}:{remote}:ro']
        if self.image_loader and self.image_loader != 'none':
            cmd.append(self.image)
            cmd.append(self.image_loader)
            return cmd + [remote, *tail]
        return cmd + [self.image, remote, *tail]

    def run(self, data):
        # O ELF pode não ter bit de execução: usa-se sempre a loader.
        proc = subprocess.run(self._cmd(), input=data, capture_output=True,
                              timeout=TIMEOUT, env={**os.environ, 'LC_ALL': 'C'})
        return proc.returncode, proc.stdout, proc.stderr

    def libc(self):
        try:
            if self.name == 'native':
                cmd = ['getconf', 'GNU_LIBC_VERSION']
            else:
                cmd = ['docker', 'run', '--rm', self.image, 'getconf', 'GNU_LIBC_VERSION']
            return subprocess.run(cmd, capture_output=True, timeout=120,
                                  text=True).stdout.strip() or '?'
        except (OSError, subprocess.SubprocessError):
            return '?'


def pick_backend(choice, binary, image, image_binary=None, image_loader=LOADER):
    native = (platform.system() == 'Linux' and platform.machine() == 'x86_64'
              and Path(LOADER).exists())
    docker = False
    if shutil.which('docker'):
        try:
            docker = subprocess.run(['docker', 'info'], capture_output=True,
                                    timeout=30).returncode == 0
        except (OSError, subprocess.SubprocessError):
            pass
    if choice in ('auto', 'native') and native:
        return Backend('native', binary)
    if choice in ('auto', 'docker') and docker:
        return Backend('docker', binary, image, image_binary, image_loader)
    return None


def load_p2():
    spec = importlib.util.spec_from_file_location('p2_for_p5', ROOT / 'out/p2_program.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_cases(binary, seed):
    """Devolve [(categoria, nome, bytes)] com rota válida, inválidas e parciais."""
    maze = decode_maze(maze_table(binary))
    route = solve(maze).encode()
    visited, _ = trace(maze, route.decode())
    # passo (1-based) em que cada checkpoint é cumprido, na ordem
    marks, nxt = [], 0
    for step, pos in enumerate(visited[1:], 1):
        if nxt < len(maze.checkpoints) and pos == maze.checkpoints[nxt]:
            marks.append(step)
            nxt += 1
    rng = random.Random(seed)
    swap = {ord('u'): b'd', ord('d'): b'u', ord('l'): b'r', ord('r'): b'l'}
    cases = [('valida', 'rota P4', route),
             ('valida', 'rota + newline CRLF', route + b'\r\n'),
             ('valida', 'whitespace inicial', b' \t\n' + route),
             ('valida', 'lixo após whitespace', route + b' extra')]
    cases += [('parcial', f'prefixo {n}/254', route[:n])
              for n in (0, 1, 17, 100, 200, 253)]
    for i, step in enumerate(marks, 1):
        cases.append(('parcial', f'até checkpoint {i} (passo {step}) + resto "r"',
                      route[:step] + b'r' * (254 - step)))
        cases.append(('parcial', f'até checkpoint {i}, resto truncado', route[:step]))
    cases += [('parcial', 'rota + 1 passo extra', route + b'r'),
              ('parcial', 'rota + 100 passos extras', route + b'u' * 100)]
    for i in (0, 1, 50, 127, 200, 253):
        bad = bytearray(route)
        bad[i:i + 1] = swap[route[i]]
        cases.append(('invalida', f'direção invertida no passo {i + 1}', bytes(bad)))
    cases += [('invalida', 'vazia', b''),
              ('invalida', 'só newline', b'\n'),
              ('invalida', '254 x "r"', b'r' * 254),
              ('invalida', '254 x "x"', b'x' * 254),
              ('invalida', 'zigue-zague lr', b'lr' * 127),
              ('invalida', 'zigue-zague du', b'du' * 127),
              ('invalida', 'bytes 0xff', b'\xff' * 254),
              ('invalida', 'NUL no início', b'\0' + route),
              ('invalida', 'NUL no meio', route[:100] + b'\0' + route[101:]),
              ('invalida', 'espaço no meio', route[:100] + b' ' + route[101:]),
              ('invalida', 'maiúsculas', route.upper())]
    for k in range(12):
        bad = bytearray(route)
        for idx in rng.sample(range(254), rng.choice((1, 1, 2, 5))):
            bad[idx] = rng.choice(b'urdlx')
        cases.append(('invalida', f'mutação aleatória #{k}', bytes(bad)))
    for k in range(12):
        n = rng.choice((254, 254, rng.randrange(1, 400)))
        cases.append(('invalida', f'aleatória #{k} (len {n})',
                      bytes(rng.choice(b'urdlx') for _ in range(n))))
    return route, cases


def expected_stdout(result):
    out = PROMPT
    if result.flag:
        out += ('Flag: ' + result.flag + '\n').encode('latin-1')
    return out


def validate(args):
    failures, report = [], {}
    binary = args.binary.resolve()
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    expected_hash = args.sha256_file.read_text().split()[0]
    print(f'[0] SHA-256 {digest[:16]}… ', end='')
    if digest != expected_hash or digest != PROFILE:
        print('DIFERENTE do perfil auditado')
        return 1, {'sha256': digest}
    print('OK')
    report['sha256'] = digest

    route, cases = build_cases(binary, args.seed)
    if args.path.exists() and args.path.read_bytes().strip() != route:
        failures.append('out/maze_path.txt difere da rota regenerada pelo solver P4')
    print(f'[1] Solver P4: {len(route)} movimentos; {len(cases)} casos de teste gerados')

    table = load_table(binary)
    p2 = load_p2()
    rows = []
    print('[2] Emulador P3 x modelo P2 (estado final)')
    for category, name, data in cases:
        r3 = Machine(table, data).run(max_steps=args.max_steps)
        r2 = p2.run(data)
        ok = (r3.status, r3.accepted, r3.flag) == (r2.status, r2.accepted, r2.flag)
        if not ok:
            failures.append(f'P3 != P2 em "{name}": {(r3.status, r3.flag)} vs {(r2.status, r2.flag)}')
        rows.append({'categoria': category, 'caso': name, 'tamanho': len(data),
                     'status': r3.status, 'aceita': r3.accepted,
                     'instrucoes': r3.instructions, 'p3_p2': ok, 'elf': None, '_r3': r3,
                     '_data': data})
    statuses = {r['status'] for r in rows}
    print(f'    {sum(r["p3_p2"] for r in rows)}/{len(rows)} iguais; status vistos: {sorted(statuses)}')
    if not statuses >= set(range(6)):
        failures.append(f'cobertura incompleta dos status 0..5: {sorted(statuses)}')

    backend = None if args.emulator_only else pick_backend(
        args.backend, binary, args.image, args.image_binary, args.image_loader)
    if backend is None:
        if not args.emulator_only:
            print('[3] ELF original: NÃO EXECUTADO (precisa de Linux x86-64 com loader glibc ou Docker ativo).')
            print('    Rode em Linux/WSL/Docker, ou use --emulator-only para confirmar que é intencional.')
            report['elf'] = 'nao-executado'
            report['e2e'] = None
            failures.append('ELF original não executado')
    else:
        report['backend'], report['libc'] = backend.name, backend.libc()
        print(f'[3] ELF original via {backend.name} ({report["libc"]})')
        rc, out, err = backend.run(route + b'\n')
        want = 'Flag: ' + load_flag(table, route) + '\n'
        e2e = rc == 0 and out == PROMPT + want.encode() and not err
        print(f'    E2E rota P4 -> {out.decode("latin-1").strip().splitlines()[-1:]}  [{"OK" if e2e else "FALHOU"}]')
        if not e2e:
            failures.append(f'E2E falhou: rc={rc} stdout={out!r} stderr={err!r}')
        report['e2e_flag'] = want.strip()
        report['e2e'] = bool(e2e)
        for row in rows:
            rc, out, err = backend.run(row['_data'])
            row['elf'] = rc == 0 and out == expected_stdout(row['_r3']) and not err
            if not row['elf']:
                failures.append(f'ELF != P3 em "{row["caso"]}": rc={rc} stdout={out!r} stderr={err!r}')
        print(f'    stdout ELF == P3: {sum(bool(r["elf"]) for r in rows)}/{len(rows)}')

    print('\nResumo por categoria (P3==P2 / ELF==P3):')
    for cat in ('valida', 'parcial', 'invalida'):
        sub = [r for r in rows if r['categoria'] == cat]
        elf = 'n/d' if backend is None else f'{sum(bool(r["elf"]) for r in sub)}/{len(sub)}'
        print(f'  {cat:9} {sum(r["p3_p2"] for r in sub)}/{len(sub)}  {elf}')

    report['casos'] = [{k: v for k, v in r.items() if not k.startswith('_')} for r in rows]
    report['falhas'] = failures
    return (1 if failures else 0), report


def load_flag(table, route):
    result = Machine(table, route).run()
    if not result.accepted:
        raise RuntimeError('o emulador P3 rejeitou a rota do P4')
    return result.flag


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--binary', type=Path, default=ROOT / 'sprint')
    p.add_argument('--sha256-file', type=Path, default=ROOT / 'sprint.sha256')
    p.add_argument('--path', type=Path, default=ROOT / 'out/maze_path.txt')
    p.add_argument('--backend', choices=('auto', 'native', 'docker'), default='auto')
    p.add_argument('--image', default='ubuntu:24.04', help='imagem Docker (glibc 2.39)')
    p.add_argument('--image-binary', default=None,
                   help='caminho do ELF dentro da imagem; sem bind mount '
                        '(use com as imagens de docker/Dockerfile)')
    p.add_argument('--image-loader', default=LOADER,
                   help=f"loader da glibc dentro da imagem, ou 'none' para "
                        f"executar o ELF diretamente (teste sob musl)")
    p.add_argument('--emulator-only', action='store_true', help='não executa o ELF')
    p.add_argument('--seed', type=int, default=20261001)
    p.add_argument('--max-steps', type=int, default=100000)
    p.add_argument('--report', type=Path, help='grava relatório JSON')
    args = p.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    code, report = validate(args)
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    label = 'APROVADO' if code == 0 else 'REPROVADO'
    if code == 0 and args.emulator_only:
        label += ' (parcial: ELF original NÃO foi executado)'
    print('\nRESULTADO:', label)
    for failure in report.get('falhas', []):
        print('  -', failure)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
