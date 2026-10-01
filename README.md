# Sprint — Google CTF 2020 (reprodução e write-up)

Trabalho da disciplina de Cibersegurança: reprodução, análise e apresentação do desafio de *reversing* **Sprint** (Google CTF 2020), uma máquina virtual implementada inteiramente dentro de chamadas a `sprintf`.

## Estrutura

```
sprint               binário original + sprint.sha256   [entregar SÓ o binário]
src/                 extrator/disassembler (P1) e solver do labirinto (P4)
out/                 disassembly, rota e mapa ASCII gerados
docs/writeup/        write-up por etapa
docs/referencias.md  todas as fontes citadas
```

> **Não versionar** `gen_data.py` do repositório oficial: ele contém a flag e gera a senha. A entrega inclui apenas o binário.

## Reprodução rápida (etapa P1)

```bash
# 1. extrair a tabela de instruções do binário
python3 src/extract.py sprint --out out/M.bin

# 2. gerar o disassembly (texto legível + JSON estruturado)
python3 src/disasm.py out/M.bin --json out/sprint.json --txt out/sprint.asm

# (opcional) conferir a integridade do binário
sha256sum -c sprint.sha256
```

Não há dependências externas (Python 3, biblioteca padrão apenas).

## Lifting e programa estruturado (etapa P2 — Antonio)

O P2 consome o JSON do P1, confere as strings com o ELF e recupera os acessos
indiretos, os registradores `r0..r7` e os dois destinos de cada desvio de baixo
byte. A organização em laços é um modelo manual auditado para o hash do Sprint
original. São **146 instruções reais**; os dois registros P1 em `0xf000` e
`0xf102` são dados. O mapa genérico de nomes do P1 não deve ser usado como mapa
concreto de registradores; o P2 recupera a semântica pelo campo `raw`.

```bash
python3 src/lift.py out/sprint.json --binary sprint --out-dir out
python3 out/p2_program.py --input out/maze_path.txt --json
python3 -m unittest discover -s tests -v
```

Saídas: `out/p2_ir.json`, `out/p2_pseudocode.txt` e `out/p2_program.py`. O Python
gerado explica e executa o crivo, a validação de comprimento e de percurso e a
decifração sem `sprintf`; funciona também no macOS com Python 3.9+. Os testes
P2 comparam o modelo com uma referência de IR, sem executar o ELF original.

## Solver do labirinto (etapa P4)

```bash
python3 src/solve_maze.py sprint --path-out out/maze_path.txt --map-out out/maze_map.txt
wc -c out/maze_path.txt   # 255 bytes: 254 movimentos + newline
sha256sum -c sprint.sha256
getconf GNU_LIBC_VERSION
/lib64/ld-linux-x86-64.so.2 ./sprint < out/maze_path.txt
python3 -m unittest discover -s tests -v
```

O script lê o símbolo `M` do **binário original** usando o extrator P1. Reconstrói o crivo de primos, usa os 256 índices em `M[0xf000:0xf100]` para formar a grade 16×16 e decodifica o início (`M[0xf100]`) e os nove checkpoints (`M[0xf103:0xf10c]`). A busca em largura usa o estado `(posição, próximo checkpoint)`; assim visita os nove pontos **na ordem exigida**. Ela exige uma rota mínima com 254 movimentos, todos dentro da grade e em células livres. A senha fica em [out/maze_path.txt](out/maze_path.txt) e a visualização para slides em [out/maze_map.txt](out/maze_map.txt). Detalhes e evidências: [write-up P4](docs/writeup/04-p4-solver.md). 

Neste checkout, `sprint` não tem o bit de execução; a chamada pela loader acima executa os **mesmos bytes** sem alterar o arquivo. Com glibc 2.39, a rota gerada imprimiu `Flag: CTF{n0w_ev3n_pr1n7f_1s_7ur1ng_c0mpl3te}`. A auditoria recebida também relata sucesso com glibc 2.44; registre a versão usada ao reproduzir.

## Ambiente

- Binário: ELF x86-64 PIE, não *stripped*. SHA-256 em `sprint.sha256`.
- glibc de referência: 2.39 (registrar sempre a versão usada — ver write-up).
- Motivo: `%4$s` lê o próprio buffer de saída de `sprintf` (comportamento indefinido, determinístico na glibc alvo).

## Divisão do trabalho (11 pessoas)

| Frente | Pessoas | Entrega |
|---|---|---|
| Código / ISA | P1–P4 | extração+disassembly, lifting, emulador, solver do labirinto |
| Testes e ambiente | P5–P6 | validação ponta a ponta, matriz de glibc, Docker |
| Slides e teoria | P7–P9 | semântica de format strings, Turing-completude, roteiro/demo |
| Write-up e repositório | P10–P11 | documento técnico, README e referências |

Este repositório contém as entregas **P1** (Rafaela), **P2** (Antonio) e **P4** (Cauã):
ver `docs/writeup/01-p1-extracao-disassembly.md`, `src/lift.py`,
`out/p2_pseudocode.txt`, `out/p2_program.py` e `docs/writeup/04-p4-solver.md`.
