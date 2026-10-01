#!/usr/bin/env python3
"""Modelo estruturado do Sprint, especializado pelo lifter P2.

Não é um emulador da ISA. O lifter verifica o perfil do ELF e insere os dados
extraídos antes deste código para produzir out/p2_program.py independente.
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Result:
    status: int
    accepted: bool
    position: int
    checkpoints: int
    steps: int
    flag: str = ""


def sieve_nonprime() -> tuple:
    """Resultado dos words em 0x7000 + 2*n; 1 = não primo."""
    nonprime = [0] * 256
    nonprime[0] = nonprime[1] = 1
    for candidate in range(2, 256):
        if not nonprime[candidate]:
            for multiple in range(2 * candidate, 256, candidate):
                nonprime[multiple] = 1
    return tuple(nonprime)


def scan_password(data: bytes) -> bytes:
    """Modela %255s para entrada em bytes e whitespace ASCII (locale C)."""
    data = data.lstrip(b" \t\n\r\v\f")
    token = bytearray()
    for byte in data:
        if byte in b" \t\n\r\v\f" or len(token) == 255:
            break
        token.append(byte)
    # A VM percorre a string até o primeiro byte NUL.
    return bytes(token).split(b"\x00", 1)[0]


def decrypt_flag(password: bytes) -> str:
    """Quatro direções formam um byte em base 4; soma ao byte cifrado."""
    digits = {ord("u"): 0, ord("r"): 1, ord("d"): 2, ord("l"): 3}
    plaintext = bytearray()
    for index, encrypted in enumerate(ENCRYPTED_FLAG):
        key = 0
        for direction in password[4 * index:4 * index + 4]:
            key = 4 * key + digits[direction]
        plaintext.append((encrypted + key) & 0xFF)
    return plaintext.decode("latin-1")


def run(data: bytes) -> Result:
    """Crivo, comprimento, labirinto e decifração; preserva os status da VM.

    O binário verifica apenas o intervalo linear 0..255, sem teste explícito
    de coluna. O solver P4 usa vizinhos geométricos mais restritivos.
    Falhas de caractere/parede não param imediatamente; status pode mudar.
    """
    nonprime = sieve_nonprime()
    password = scan_password(data)
    position = START
    if len(password) != INPUT_LENGTH:
        # START ainda não foi carregado pela VM; posição é só metadado do modelo.
        return Result(5, False, position, 0, 0)
    reached = 0
    valid = True
    status = 0
    deltas = {ord("u"): -16, ord("r"): 1, ord("d"): 16, ord("l"): -1}
    for step, direction in enumerate(password, 1):
        if direction not in deltas:
            valid = False
            status = 1
        position = (position + deltas.get(direction, 0)) & 0xFFFF
        if position >> 8:
            return Result(4, False, position, reached, step)
        if nonprime[MAZE[position]]:
            valid = False
            status = 2
            continue
        # Na VM a soma com o byte negativo testa apenas os 8 bits baixos.
        # Após os nove alvos, o próximo byte lido já pertence à cifra.
        target_byte = TARGET_TAIL[reached] if reached < len(TARGET_TAIL) else 0
        if (position + target_byte) & 0xFF == 0:
            reached += 1
    if not valid:
        return Result(status, False, position, reached, len(password))
    if reached != CHECKPOINT_COUNT:
        return Result(3, False, position, reached, len(password))
    return Result(0, True, position, reached, len(password), decrypt_flag(password))


def main() -> int:
    parser = argparse.ArgumentParser(description="P2: programa estruturado do Sprint")
    parser.add_argument("--input", type=Path, help="arquivo com a entrada; padrão: stdin")
    parser.add_argument("--json", action="store_true", help="inclui estado final do modelo")
    args = parser.parse_args()
    data = args.input.read_bytes() if args.input else sys.stdin.buffer.read()
    result = run(data)
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    elif result.accepted:
        print("Flag: " + result.flag)
    else:
        print(f"Entrada rejeitada pelo modelo P2 (status {result.status})")
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
