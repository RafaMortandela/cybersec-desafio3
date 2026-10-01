#!/usr/bin/env python3
"""P2 gerado por src/lift.py. Não editar; regenere."""
# ELF SHA256: 925510065b1cd97c53bb6f46b64fbf9fe5a039aa892d6f5609e200e2c74d726a
INPUT_LENGTH = 254
CHECKPOINT_COUNT = 9
START = 17
MAZE = (204, 176, 231, 123, 188, 192, 238, 58, 252, 115, 129, 208, 122, 105, 132, 226,
 72, 227, 215, 89, 17, 107, 241, 179, 134, 11, 137, 197, 191, 83, 101, 101, 240,
 239, 106, 191, 8, 120, 196, 44, 153, 53, 60, 108, 220, 224, 200, 153, 200, 59,
 239, 41, 151, 11, 179, 139, 204, 157, 252, 5, 27, 103, 181, 173, 21, 193, 8,
 208, 69, 69, 38, 67, 69, 109, 244, 239, 187, 73, 6, 202, 115, 107, 188, 233,
 80, 151, 5, 229, 151, 211, 181, 71, 43, 173, 37, 139, 174, 175, 65, 229, 216,
 20, 244, 131, 230, 240, 192, 152, 10, 172, 161, 149, 245, 181, 211, 83, 240,
 151, 239, 157, 212, 59, 59, 11, 231, 23, 7, 31, 108, 241, 30, 68, 146, 178, 87,
 7, 183, 54, 143, 83, 201, 234, 16, 144, 98, 223, 29, 7, 179, 113, 83, 97, 26,
 43, 120, 191, 193, 181, 198, 59, 234, 43, 68, 23, 160, 132, 202, 143, 183, 59,
 56, 47, 232, 115, 132, 173, 68, 239, 248, 173, 140, 31, 234, 127, 205, 197,
 179, 73, 5, 3, 149, 167, 68, 181, 145, 105, 248, 149, 108, 229, 135, 83, 78,
 71, 146, 190, 128, 208, 128, 29, 173, 241, 61, 227, 223, 53, 97, 241, 231, 13,
 113, 197, 2, 79, 32, 94, 162, 139, 196, 97, 50, 15, 168, 190, 126, 41, 209,
 109, 42, 217, 85, 71, 7, 131, 234, 43, 121, 149, 79, 61, 163, 17, 221, 193, 29,
 137)
ENCRYPTED_FLAG = (158, 255, 161, 38, 20, 59, 104, 96, 107, 199, 52, 196, 10, 27, 109, 140, 201,
 71, 118, 101, 50, 116, 95, 226, 37, 114, 50, 116, 98, 10, 185, 129, 110, 198,
 23, 227, 197, 102, 125)
TARGET_TAIL = (131, 1, 175, 73, 173, 193, 15, 139, 225, 158, 255, 161, 38, 20, 59, 104, 96,
 107, 199, 52, 196, 10, 27, 109, 140, 201, 71, 118, 101, 50, 116, 95, 226, 37,
 114, 50, 116, 98, 10, 185, 129, 110, 198, 23, 227, 197, 102, 125, 0)

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
