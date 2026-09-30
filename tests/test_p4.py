"""Checagens do solver P4, sem executar a VM ou depender da glibc."""

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from solve_maze import Maze, decode_maze, load_table, solve, trace  # noqa: E402


class MazeSolverTests(unittest.TestCase):
    def test_checkpoint_futuro_precisa_ser_revisitado(self):
        cells = [False] * 256
        for position in (0, 1, 2):
            cells[position] = True
        maze = Maze(tuple(cells), 0, (2, 1))
        route = solve(maze)
        self.assertEqual(route, "rrl")
        self.assertEqual(trace(maze, route), ([0, 1, 2, 1], 2))

    def test_elf_original_gera_rota_valida_de_254_passos(self):
        maze = decode_maze(load_table(ROOT / "sprint"))
        self.assertEqual(maze.start, 0x11)
        self.assertEqual(maze.checkpoints,
                         (0x7D, 0xFF, 0x51, 0xB7, 0x53, 0x3F, 0xF1, 0x75, 0x1F))
        route = solve(maze)
        visited, reached = trace(maze, route)
        self.assertEqual(len(route), 254)
        self.assertEqual(len(visited), 255)
        self.assertEqual(reached, 9)
        self.assertEqual((ROOT / "out/maze_path.txt").read_text(encoding="ascii"),
                         route + "\n")


if __name__ == "__main__":
    unittest.main()
