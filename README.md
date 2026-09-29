# Sprint — Google CTF 2020 (reprodução e write-up)

Trabalho da disciplina de Cibersegurança: reprodução, análise e apresentação do desafio de *reversing* **Sprint** (Google CTF 2020), uma máquina virtual implementada inteiramente dentro de chamadas a `sprintf`.

## Estrutura

```
sprint               binário original + sprint.sha256   [entregar SÓ o binário]
src/                 extrator ELF + disassembler da ISA implícita  (P1)
out/                 artefatos gerados (M.bin, sprint.asm, sprint.json)
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

Esta parte do repositório cobre **P1** (Rafaela): ver `docs/writeup/01-p1-extracao-disassembly.md`.
