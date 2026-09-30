#!/usr/bin/env python3
"""P4: reconstrói o labirinto Sprint e acha a senha com BFS.

Os endereços são offsets dentro do símbolo M copiado para a memória da VM.
O crivo da primeira fase marca 0, 1 e os compostos; os primos permanecem
desmarcados. Cada célula guarda em M[0xf000+posição] um índice desse crivo.
"""

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from extract import Elf64, find_table


GRID = 16
SIZE = GRID * GRID
START_ADDR = 0xF100
CHECKPOINTS_ADDR = 0xF103
CHECKPOINT_COUNT = 9
INPUT_LENGTH = 254


@dataclass(frozen=True)
class Maze:
    walkable: tuple[bool, ...]
    start: int
    checkpoints: tuple[int, ...]


def load_table(binary: Path) -> bytes:
    data = binary.read_bytes()
    elf = Elf64(data)
    _, offset, size = find_table(elf)
    table = data[offset:offset + size]
    if len(table) < CHECKPOINTS_ADDR + CHECKPOINT_COUNT:
        raise ValueError("símbolo M curto demais para conter o labirinto")
    return table


def prime_mask() -> tuple[bool, ...]:
    """Replica o resultado do crivo da VM para os índices de 0 a 255."""
    prime = [True] * SIZE
    prime[0] = prime[1] = False
    for value in range(2, SIZE):
        if prime[value]:
            for multiple in range(2 * value, SIZE, value):
                prime[multiple] = False
    return tuple(prime)


def decode_maze(table: bytes) -> Maze:
    if len(table) < CHECKPOINTS_ADDR + CHECKPOINT_COUNT:
        raise ValueError("tabela M incompleta")
    primes = prime_mask()
    walkable = tuple(primes[index] for index in table[0xF000:0xF100])
    start = table[START_ADDR]
    # A VM compara (posição + byte) & 0xff == 0, avançando um checkpoint
    # apenas quando o checkpoint atual é atingido.
    checkpoints = tuple((-value) & 0xFF for value in
                        table[CHECKPOINTS_ADDR:CHECKPOINTS_ADDR + CHECKPOINT_COUNT])
    if len(walkable) != SIZE or not walkable[start]:
        raise ValueError("mapa de 16x16 ou posição inicial inválidos")
    if len(set(checkpoints)) != CHECKPOINT_COUNT or any(
        not walkable[position] for position in checkpoints
    ):
        raise ValueError("checkpoints repetidos ou bloqueados")
    return Maze(walkable, start, checkpoints)


def neighbors(position: int):
    row, col = divmod(position, GRID)
    if row > 0:
        yield "u", position - GRID
    if col < GRID - 1:
        yield "r", position + 1
    if row < GRID - 1:
        yield "d", position + GRID
    if col > 0:
        yield "l", position - 1


def trace(maze: Maze, directions: str) -> tuple[list[int], int]:
    """Valida movimentos e devolve posições visitadas e checkpoints cumpridos."""
    position = maze.start
    checkpoint = 0
    visited = [position]
    for step, direction in enumerate(directions, 1):
        moves = dict(neighbors(position))
        if direction not in moves:
            raise ValueError(f"movimento {step} sai da grade: {direction!r}")
        position = moves[direction]
        if not maze.walkable[position]:
            raise ValueError(f"movimento {step} entra em parede: {position:#04x}")
        if checkpoint < len(maze.checkpoints) and position == maze.checkpoints[checkpoint]:
            checkpoint += 1
        visited.append(position)
    return visited, checkpoint


def solve(maze: Maze) -> str:
    """BFS no estado (posição, próximo checkpoint), com rota mínima."""
    origin = (maze.start, 0)
    queue = deque([origin])
    previous = {origin: None}
    goal = None
    while queue:
        position, checkpoint = queue.popleft()
        if checkpoint == len(maze.checkpoints):
            goal = (position, checkpoint)
            break
        for direction, next_position in neighbors(position):
            if not maze.walkable[next_position]:
                continue
            next_checkpoint = checkpoint + (
                next_position == maze.checkpoints[checkpoint]
            )
            state = (next_position, next_checkpoint)
            if state not in previous:
                previous[state] = ((position, checkpoint), direction)
                queue.append(state)
    if goal is None:
        raise ValueError("não existe rota pelos checkpoints na ordem exigida")
    route = []
    while goal != origin:
        goal, direction = previous[goal]
        route.append(direction)
    return "".join(reversed(route))


def render_map(maze: Maze, route: str) -> str:
    visited, _ = trace(maze, route)
    path = set(visited)
    checkpoints = {position: str(i + 1) for i, position in enumerate(maze.checkpoints)}
    rows = ["   " + " ".join(f"{col:x}" for col in range(GRID))]
    for row in range(GRID):
        symbols = []
        for col in range(GRID):
            position = row * GRID + col
            if position == maze.start:
                symbol = "S"
            elif position in checkpoints:
                symbol = checkpoints[position]
            elif not maze.walkable[position]:
                symbol = "#"
            elif position in path:
                symbol = "*"
            else:
                symbol = "."
            symbols.append(symbol)
        rows.append(f"{row:x}  " + " ".join(symbols))
    rows.append("S início; 1-9 checkpoints em ordem; # parede; * rota; . livre")
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, help="ELF sprint original")
    parser.add_argument("--path-out", type=Path, help="grava a senha com quebra de linha")
    parser.add_argument("--map-out", type=Path, help="grava mapa ASCII com a rota")
    args = parser.parse_args()

    maze = decode_maze(load_table(args.binary))
    route = solve(maze)
    _, reached = trace(maze, route)
    if len(route) != INPUT_LENGTH or reached != CHECKPOINT_COUNT:
        raise ValueError(
            f"rota mínima incompatível: {len(route)} passos, {reached} checkpoints; "
            f"o desafio exige {INPUT_LENGTH} passos e {CHECKPOINT_COUNT} checkpoints"
        )
    if args.path_out:
        args.path_out.write_text(route + "\n", encoding="ascii")
        print(f"senha de {len(route)} movimentos gravada em {args.path_out}")
    else:
        print(route)
    if args.map_out:
        args.map_out.write_text(render_map(maze, route), encoding="utf-8")
        print(f"mapa gravado em {args.map_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
