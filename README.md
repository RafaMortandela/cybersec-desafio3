# Sprint — Google CTF 2020 (reprodução e write-up)

Trabalho da disciplina de Cibersegurança: reprodução, análise e apresentação do desafio de *reversing* **Sprint** (Google CTF 2020), uma máquina virtual implementada inteiramente dentro de chamadas a `sprintf`.

**Fluxo da solução:** binário → ISA implícita → programa (crivo de primos + labirinto) → senha → flag.

- Slides: [apresentação no Canva](https://canva.link/7p0fq9fc7v580ud)
- Referências completas: [docs/referencias.md](docs/referencias.md)

## Sumário

1. [Estrutura do repositório](#estrutura-do-repositório)
2. [Pré-requisitos e ambiente](#pré-requisitos-e-ambiente)
3. [Reprodução passo a passo](#reprodução-passo-a-passo)
4. [Etapas e entregas](#etapas-e-entregas)
5. [Divisão do trabalho](#divisão-do-trabalho)
6. [Licença](#licença)

## Estrutura do repositório

```
sprint                  binário original do desafio
sprint.sha256           hash SHA-256 do binário
src/                    extrator/disassembler (P1), lifting (P2), emulador (P3),
                        solver do labirinto (P4) e validação (P5)
tests/                  testes automatizados (P2, P3, P4, P5, P6)
out/                    artefatos gerados: disassembly, IR, pseudocódigo,
                        rota e mapa do labirinto, resultados de P3 e matriz P6
docker/                 Dockerfiles e matriz de ambientes (P6)
docs/writeup/           write-up por etapa
docs/referencias.md     todas as fontes citadas
docs/revisao-coesao.md  revisão de coerência entre notas, código e write-ups
LICENSE                 licença do repositório
```

> **Não versionar** `gen_data.py` do repositório oficial: ele contém a flag e gera a senha. A solução não depende dele; dos arquivos do desafio oficial, a entrega inclui apenas o binário.

## Pré-requisitos e ambiente

- **Python 3.9+**, sem dependências externas (apenas biblioteca padrão).
- **Linux x86-64 com glibc** para executar o binário original. Em outros sistemas, use o emulador (P3) e a validação `--emulator-only` da etapa P5: ambos leem o arquivo `sprint` para extrair os dados, mas não executam o ELF.
- **Docker ativo com suporte a `linux/amd64`** para executar o ELF em macOS/Windows ou reproduzir a matriz P6. Os scripts Python rodam na máquina local; o ELF roda no container.
- Binário: ELF x86-64 PIE, não *stripped*.
- glibc de referência: **2.39**. Registre sempre a versão usada no ambiente que executa o ELF (`getconf GNU_LIBC_VERSION`). Os relatórios versionados de P6 incluem sucesso com a glibc 2.44.
- Por que a glibc importa: `%4$s` lê o próprio buffer de saída do `sprintf`, comportamento indefinido que é determinístico na glibc alvo.
- Docker e matriz de versões de glibc: ver [Ambiente Docker (P6)](#ambiente-docker-e-matriz-de-glibc-p6).

## Reprodução passo a passo

Execute os comandos na raiz do repositório. Os artefatos de `out/` já estão versionados, permitindo executar cada etapa com suas entradas prontas. Para regenerar os artefatos, rode na ordem **P1 → P4 → P2 → P3 → P5**: P2 usa o JSON de P1, e os exemplos de P2/P3 usam a rota de P4. P5 regenera a rota internamente e compara P3 com o programa P2 gerado.

```bash
# 0. conferir a integridade do binário
sha256sum -c sprint.sha256

# P1: extrair a tabela de instruções e gerar o disassembly
python3 src/extract.py sprint --out out/M.bin
python3 src/disasm.py out/M.bin --json out/sprint.json --txt out/sprint.asm

# P4: resolver o labirinto (gera a senha de 254 movimentos)
python3 src/solve_maze.py sprint --path-out out/maze_path.txt --map-out out/maze_map.txt

# P2: lifting para pseudocódigo e programa estruturado
python3 src/lift.py out/sprint.json --binary sprint --out-dir out
python3 out/p2_program.py --input out/maze_path.txt --json

# P3: emulador próprio (sem sprintf)
python3 src/emulate.py --input out/maze_path.txt --json

# P5: em Linux x86-64 com glibc, validação ELF x P3 x P2
python3 src/validate.py

# todos os testes automatizados
python3 -m unittest discover -s tests -v
```

No macOS, confira o hash com `shasum -a 256 -c sprint.sha256` no lugar de `sha256sum`. Para P5 sem execução do ELF, use `python3 src/validate.py --emulator-only`; para validar o ELF em Docker, use os comandos da seção [P5](#p5--validação).

**Conferir a flag no binário original em Linux x86-64 com glibc.** Neste checkout o arquivo `sprint` não tem o bit de execução. A chamada pelo loader executa os mesmos bytes sem alterar o arquivo:

```bash
/lib64/ld-linux-x86-64.so.2 ./sprint < out/maze_path.txt
```

Com a glibc 2.39, a saída esperada é:

```
Flag: CTF{n0w_ev3n_pr1n7f_1s_7ur1ng_c0mpl3te}
```

## Etapas e entregas

### P1 — Extração e disassembly

Lê do binário a tabela de strings de formato e os endereços, e classifica cada string em uma instrução da ISA implícita. A saída é um disassembly legível (`out/sprint.asm`) e estruturado (`out/sprint.json`).
Write-up: [01-p1-extracao-disassembly.md](docs/writeup/01-p1-extracao-disassembly.md).

### P2 — Lifting para pseudocódigo

Consome o JSON do P1, confere as strings com o ELF e recupera os acessos indiretos, os registradores `r0..r7` e os dois destinos de cada desvio de baixo byte. São **146 instruções reais**; os dois registros do P1 em `0xf000` e `0xf102` são dados. O mapa genérico de nomes do P1 não deve ser usado como mapa concreto de registradores: o P2 recupera a semântica pelo campo `raw`.

A organização em laços é um modelo manual auditado para o hash do Sprint original. O Python gerado explica e executa o crivo, a validação de comprimento e de percurso e a decifração sem `sprintf`, e funciona também no macOS com Python 3.9+.

Saídas: `out/p2_ir.json`, `out/p2_pseudocode.txt` e `out/p2_program.py`. Os testes do P2 comparam o modelo com uma referência de IR, sem executar o ELF original.

### P3 — Emulador próprio

Interpretador da ISA recuperada que executa o programa diretamente das strings extraídas do ELF, **sem `sprintf`**, sem o P2 e sem o solver. Oferece memória, registradores, execução passo a passo, trace JSONL e limite de instruções.

```bash
python3 src/emulate.py --input out/maze_path.txt --trace out/p3_trace.jsonl
```

A rota válida termina após 19.234 instruções e recupera a flag. As saídas do emulador são comparadas com o P2 e com o stdout do ELF original (ver P5).
Write-up: [03-p3-emulador.md](docs/writeup/03-p3-emulador.md).

### P4 — Solver do labirinto

Lê o símbolo `M` do **binário original** usando o extrator do P1, reconstrói o crivo de primos e usa os 256 índices em `M[0xf000:0xf100]` para formar a grade 16×16. Decodifica o início (`M[0xf100]`) e os nove checkpoints (`M[0xf103:0xf10c]`). A busca em largura usa o estado `(posição, próximo checkpoint)`, visitando os nove pontos **na ordem exigida**, e exige uma rota mínima de 254 movimentos dentro da grade e em células livres.

A senha fica em [out/maze_path.txt](out/maze_path.txt) (255 bytes: 254 movimentos + newline) e a visualização para os slides em [out/maze_map.txt](out/maze_map.txt).
Write-up: [04-p4-solver.md](docs/writeup/04-p4-solver.md).

### P5 — Validação

Script ponta a ponta: executa o binário original com a entrada gerada pelo P4 e confere que a flag aparece. Também faz testes diferenciais entre o ELF, o emulador (P3) e o modelo do P2, com entradas válidas, parciais e inválidas.

```bash
python3 src/validate.py                  # E2E com o ELF + diferencial ELF x P3 x P2
python3 src/validate.py --emulator-only  # compara P3 x P2 sem executar o ELF

# E2E em Docker (ex.: macOS ou Windows, com Docker ativo)
docker build --platform linux/amd64 -t sprint-p6:ref-2.39 -f docker/Dockerfile .
python3 src/validate.py --backend docker --image sprint-p6:ref-2.39 --image-binary /sprint
```

`--emulator-only` é uma validação parcial: não confirma o comportamento da libc nem a saída do ELF original. A suíte `unittest` também ignora o teste diferencial nativo com o ELF fora de Linux x86-64 com o loader esperado; o comando Docker acima faz essa validação separadamente.

### Ambiente Docker e matriz de glibc (P6)

```bash
python3 docker/matrix.py                 # constrói e roda a matriz inteira
python3 docker/matrix.py --report-only   # só resume relatórios existentes
```

Usa `docker/Dockerfile` (base fixada por digest) e `docker/Dockerfile.nix` (Nixpkgs fixado). O binário é copiado para a imagem com o hash conferido no build, sem bind mount. Os relatórios versionados registram concordância das 71 entradas de P5 em **glibc 2.31, 2.35, 2.36, 2.39, 2.40 e 2.44**; o write-up também relata sucesso no host glibc 2.43. Sob **musl** (Alpine), o ELF não inicia porque seu loader `/lib64/ld-linux-x86-64.so.2` está ausente; a matriz registra essa falha como esperada. Resultado consolidado em [out/p6/matriz.tsv](out/p6/matriz.tsv) e detalhes no [write-up P6](docs/writeup/06-p6-ambiente-glibc.md). `gen_data.py` fica fora da entrega e é barrado no contexto de build pelo `.dockerignore`.

### Write-up técnico (P10)

O documento principal que consolida a metodologia de engenharia reversa do grupo, justificando as decisões arquiteturais e detalhando formalmente **o que acrescentamos aos materiais públicos** (como a matriz de execução multi-ambiente e o desacoplamento das ferramentas). 

Leia o documento finalizado em: [docs/writeup/10-p10-writeup-tecnico.md](docs/writeup/10-p10-writeup-tecnico.md). 
    
Os demais write-ups divididos por etapa continuam disponíveis na pasta [`docs/writeup/`](docs/writeup/).

## Divisão do trabalho

Grupo de 11 pessoas.

| Frente | Etapas | Entrega |
|---|---|---|
| Código / ISA | P1–P4 | extração + disassembly, lifting, emulador, solver do labirinto |
| Testes e ambiente | P5–P6 | validação ponta a ponta, matriz de glibc, Docker |
| Slides e teoria | P7–P9 | semântica de format strings, Turing-completude, roteiro/demo |
| Write-up e repositório | P10–P11 | documento técnico, README e referências |

## Licença

Ver [LICENSE](LICENSE). O desafio original pertence ao Google CTF 2020; este repositório contém o binário original e material de análise e reprodução desenvolvido pelo grupo.
