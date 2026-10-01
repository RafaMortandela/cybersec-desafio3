"""P6: regras de ambiente/entrega que não dependem de Docker nem de glibc.

Verifica que a solução é autossuficiente a partir do ELF: o binário corresponde
ao perfil auditado e nenhum módulo ou imagem oficial depende de gen_data.py (o
gerador oficial, que contém a flag e deve ficar fora do repositório entregue).
"""

import ast
import hashlib
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class AmbienteTests(unittest.TestCase):
    def test_binario_confere_com_perfil_e_com_sha256_file(self):
        digest = hashlib.sha256((ROOT / "sprint").read_bytes()).hexdigest()
        self.assertEqual(digest, (ROOT / "sprint.sha256").read_text().split()[0])
        from emulate import PROFILE

        self.assertEqual(digest, PROFILE)

    def test_gen_data_ausente_e_nao_referenciado(self):
        self.assertEqual(list(ROOT.rglob("gen_data.py")), [])
        for source in (ROOT / "src").glob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            importados = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    importados.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    importados.add(node.module.split(".")[0])
            self.assertNotIn("gen_data", importados, source.name)

    def test_dockerfiles_fixam_digest(self):
        for dockerfile in (ROOT / "docker").glob("Dockerfile*"):
            texto = dockerfile.read_text(encoding="utf-8")
            for linha in re.findall(r"^FROM\s+(.+)$", texto, re.M):
                base = linha.split()[-1]
                if base.startswith("${"):
                    continue
                self.assertIn("sha256:", base,
                              f"{dockerfile.name}: base {base} sem digest fixo")

    def test_solucao_nao_usa_gerador_oficial(self):
        # A rota nasce do próprio ELF; se o gerador fosse necessário, o build
        # das imagens (sem gen_data.py) e estes testes não seriam suficientes.
        from solve_maze import decode_maze, solve, load_table
        from emulate import Machine, load_table as tabela_vm

        maze = decode_maze(load_table(ROOT / "sprint"))
        route = solve(maze)
        result = Machine(tabela_vm(ROOT / "sprint"), route.encode()).run()
        self.assertTrue(result.accepted)
        self.assertTrue(result.flag.startswith("CTF{"))


if __name__ == "__main__":
    unittest.main()