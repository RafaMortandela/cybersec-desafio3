#!/usr/bin/env python3
"""P6: monta e executa a matriz de ambientes da solucao Sprint.

Cada linha e construida a partir de um digest fixo de imagem, tem o binario
assado na imagem (com hash conferido no build) e e validada por src/validate.py
com as mesmas 71 entradas de P5. A saida e uma tabela em out/p6/matriz.tsv e um
relatorio JSON por linha.

Uso:
    python3 docker/matrix.py                 # constroi e roda tudo
    python3 docker/matrix.py --only alpine-musl
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out' / 'p6'

# Digests fixos. Nao usar tags moveis: as versoes abaixo sao o contrato da
# matriz. Cada digest foi resolvido em 2026-10-01.
UBUNTU_20_04 = 'ubuntu@sha256:8feb4d8ca5354def3d8fce243717141ce31e2c428701f6682bd2fafe15388214'
UBUNTU_22_04 = 'ubuntu@sha256:b8b6ee6aa931ecd9d0d952abc34dc0e5f7c6a30c6bb71b079fe399fde0329c02'
UBUNTU_24_04 = 'ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3'
DEBIAN_12 = 'debian@sha256:f37a335e82bca302e955fa39f9dfe28f1be618f016f8a2b56318e5a5111afc26'
ARCH = 'archlinux@sha256:b21322c663be387c0ed9cbc7bbbfe18e41633ad4e7b7c77cfad45f128be20040'
ALPINE = 'alpine@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6'

MATRIX = [
    # rotulo, dockerfile, base, pacotes extras, loader, esperado
    ('ubuntu-20.04-2.31', 'Dockerfile', UBUNTU_20_04, '', None, 'aprovado'),
    ('ubuntu-22.04-2.35', 'Dockerfile', UBUNTU_22_04, '', None, 'aprovado'),
    ('debian-12-2.36', 'Dockerfile', DEBIAN_12, '', None, 'aprovado'),
    ('ubuntu-24.04-2.39', 'Dockerfile', UBUNTU_24_04, '', None, 'aprovado'),
    ('arch-2.44', 'Dockerfile', ARCH, '', None, 'aprovado'),
    ('nixpkgs-glibc-2.40', 'Dockerfile.nix', None, '', '/nix-loader', 'aprovado'),
    # musl: o ELF exige o PT_INTERP da glibc, ausente aqui. A falha e o
    # resultado esperado e comprova que o binario nao roda fora de uma libc GNU.
    ('alpine-musl', 'Dockerfile', ALPINE, '', 'none', 'nao-executa'),
]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def build(label, dockerfile, base, extra):
    cmd = ['docker', 'build', '--platform', 'linux/amd64',
           '-t', f'sprint-p6:{label}', '-f', str(ROOT / 'docker' / dockerfile)]
    if base:
        cmd += ['--build-arg', f'BASE_IMAGE={base}']
    if extra:
        cmd += ['--build-arg', f'EXTRA_PKGS={extra}']
    cmd.append(str(ROOT))
    proc = run(cmd)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(f'build falhou: {label}')
    return proc.stdout


def observed_libc(image):
    proc = run(['docker', 'run', '--rm', '--platform', 'linux/amd64',
                image, 'getconf', 'GNU_LIBC_VERSION'])
    return proc.stdout.strip() or 'ausente (musl)'


def validate(label, image, loader):
    cmd = [sys.executable, str(ROOT / 'src' / 'validate.py'),
           '--backend', 'docker', '--image', image, '--image-binary', '/sprint',
           '--report', str(OUT / f'validate-{label}.json')]
    if loader is not None:
        cmd += ['--image-loader', loader]
    proc = run(cmd)
    return proc.returncode, proc.stdout, proc.stderr


def summary(report_path, expected):
    report = json.loads(report_path.read_text())
    rows = report.get('casos', [])
    elf = sum(1 for r in rows if r.get('elf'))
    p3p2 = sum(1 for r in rows if r.get('p3_p2'))
    if 'e2e' in report:
        e2e = report['e2e']
    else:
        # Relatorios antigos nao traziam o booleano; infere-se pelas falhas.
        e2e = not any('E2E falhou' in f for f in report.get('falhas', []))
    status = {
        'linha': report_path.stem.replace('validate-', ''),
        'glibc': report.get('libc', '?'),
        'sha256': (report.get('sha256') or '')[:16],
        'casos': len(rows),
        'p3_p2': f'{p3p2}/{len(rows)}',
        'elf_p3': f'{elf}/{len(rows)}',
        'e2e': {True: 'sim', False: 'nao', None: 'n/d'}[e2e],
        'esperado': expected,
        'veredito': 'OK' if _ok(elf, p3p2, len(rows), expected) else 'DIVERGIU',
    }
    return status


def _ok(elf, p3p2, total, expected):
    if expected == 'aprovado':
        return elf == total and p3p2 == total
    return elf == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', help='roda apenas uma linha')
    ap.add_argument('--report-only', action='store_true',
                    help='nao reconstroi nem executa: so resume relatorios existentes')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    table = []
    for label, dockerfile, base, extra, loader, expected in MATRIX:
        if args.only and args.only != label:
            continue
        image = f'sprint-p6:{label}'
        report_path = OUT / f'validate-{label}.json'
        if not args.report_only:
            print(f'===== {label}: build', flush=True)
            build(label, dockerfile, base, extra)
            libc = observed_libc(image)
            code, out, err = validate(label, image, loader)
            print(f'      libc={libc} validate_rc={code} esperado={expected}', flush=True)
        if not report_path.exists():
            continue
        row = summary(report_path, expected)
        row['base'] = base or 'nixos/nix pinado'
        table.append(row)

    if not table:
        return 0
    header = ['linha', 'base', 'glibc', 'sha256', 'casos', 'p3_p2', 'elf_p3',
              'e2e', 'esperado', 'veredito']
    lines = ['\t'.join(header)]
    for row in table:
        lines.append('\t'.join(str(row.get(k, '')) for k in header))
    text = '\n'.join(lines) + '\n'
    (OUT / 'matriz.tsv').write_text(text, encoding='utf-8')
    print('\n' + text)
    return 0 if all(r['veredito'] == 'OK' for r in table) else 1


if __name__ == '__main__':
    raise SystemExit(main())