# P6 — Ambiente e matriz de glibc

Esta etapa fixa o ambiente de execução, executa o binário original em várias
distribuições e versões de libc e registra onde o comportamento indefinido (UB)
do `sprintf` com `%4$s` se mantém e onde quebra. Tudo parte do **binário
original** com o hash auditado; a senha é regenerada por `src/solve_maze.py`
a partir do próprio ELF. `gen_data.py` não é usado nem incluído.

## Entregáveis

```
docker/Dockerfile       imagem genérica; a base vem por digest (BASE_IMAGE)
docker/Dockerfile.nix   imagem com Nixpkgs fixado por revisão
docker/matrix.py        monta as imagens e roda src/validate.py em cada linha
.dockerignore           garante que gen_data.py nunca entra no contexto de build
out/p6/matriz.tsv       resultado consolidado da matriz
out/p6/validate-*.json  relatório de P5 por ambiente
```

## Imagens fixadas

Cada linha usa um digest, resolvido em 2026-10-01 e conferido no build. A versão
de glibc foi **observada** com `getconf GNU_LIBC_VERSION` dentro do container, não
inferida da tag.

| Linha | Base (digest fixo) | glibc observada |
|---|---|---|
| ubuntu-20.04-2.31 | `ubuntu@sha256:8feb4d8ca5354def3d8fce243717141ce31e2c428701f6682bd2fafe15388214` | 2.31 |
| ubuntu-22.04-2.35 | `ubuntu@sha256:b8b6ee6aa931ecd9d0d952abc34dc0e5f7c6a30c6bb71b079fe399fde0329c02` | 2.35 |
| debian-12-2.36 | `debian@sha256:f37a335e82bca302e955fa39f9dfe28f1be618f016f8a2b56318e5a5111afc26` | 2.36 |
| ubuntu-24.04-2.39 | `ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3` | 2.39 (referência) |
| arch-2.44 | `archlinux@sha256:b21322c663be387c0ed9cbc7bbbfe18e41633ad4e7b7c77cfad45f128be20040` | 2.44 |
| nixpkgs-glibc-2.40 | `nixos/nix@sha256:a09d508c2e46d3a4c7205ff3fa0d506d626a5a966c31e879df7efe737e22f003` + Nixpkgs `50ab793786d9de88ee30ec4e4c24fb4236fc2674` | 2.40 |
| alpine-musl | `alpine@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6` | musl (sem glibc) |

O host de teste (Fedora, glibc 2.43) também foi rodado nativamente e passou.
A versão de referência do projeto continua sendo **glibc 2.39** (Ubuntu 24.04).
Os IDs de imagem não são registrados: dependem do build local e não são
contrato. O que é contrato são os digests de base acima e o hash do binário,
ambos verificados automaticamente.

## Como reproduzir

```bash
python3 docker/matrix.py            # constrói e roda a matriz inteira
python3 docker/matrix.py --report-only   # só resume relatórios existentes

# uma linha isolada
docker build --platform linux/amd64 -t sprint-p6:ubuntu-24.04-2.39 -f docker/Dockerfile .
python3 src/validate.py --backend docker --image sprint-p6:ubuntu-24.04-2.39 \
    --image-binary /sprint --report out/p6/validate-ubuntu-24.04-2.39.json
```

Requisitos: Docker com `linux/amd64` e Python 3 na máquina. Nenhuma dependência
além da biblioteca padrão.

## Resultado

As mesmas 71 entradas de P5 (rota válida, parciais e inválidas) foram executadas
em cada ambiente. `P3×P2` compara o estado final do emulador com o modelo
estruturado; `ELF×P3` compara o stdout do binário original com o esperado.

| Linha | glibc | P3×P2 | ELF×P3 | E2E (flag) | Veredito |
|---|---|---|---|---|---|
| ubuntu-20.04-2.31 | 2.31 | 71/71 | 71/71 | sim | OK |
| ubuntu-22.04-2.35 | 2.35 | 71/71 | 71/71 | sim | OK |
| debian-12-2.36 | 2.36 | 71/71 | 71/71 | sim | OK |
| ubuntu-24.04-2.39 | 2.39 | 71/71 | 71/71 | sim | OK |
| arch-2.44 | 2.44 | 71/71 | 71/71 | sim | OK |
| nixpkgs-glibc-2.40 | 2.40 | 71/71 | 71/71 | sim | OK |
| alpine-musl | musl | 71/71 | 0/71 | não executa | OK (esperado) |

O binário não inicia sob musl: o `PT_INTERP` é `/lib64/ld-linux-x86-64.so.2`,
ausente no Alpine, e o kernel falha com `rc=255`, `exec /sprint: no such file or
directory`. Isso confirma que o ELF **exige** uma libc GNU e não é um caso de
divergência da VM. Nas sete linhas com glibc (2.31 a 2.44), incluindo o host de
teste Fedora com glibc 2.43, a flag e o stdout foram idênticos ao emulador.

## Adaptações registradas

- **Sem bind mount.** O binário é copiado para a imagem (`COPY --chmod=0555`) e o
  hash é conferido no build; se divergir do perfil, a imagem não é construída.
  Em hosts com SELinux `Enforcing` (Fedora/RHEL), montar `$HOME` via `-v` é
  negado e o ELF falha com `rc=127 /sprint: cannot open shared object file:
  Permission denied` em **todas** as linhas — um falso negativo que parece
  divergência de libc. Assar o binário elimina essa classe de erro e torna o
  digest da imagem um atestado do binário.
- **Loader explícito.** Como o arquivo do repositório pode não ter bit de
  execução, a execução nas imagens glibc usa `/lib64/ld-linux-x86-64.so.2` sobre
  `/sprint`, sem alterar o arquivo. Na linha musl usa-se execução direta
  (`--image-loader none`), deixando o kernel resolver o `PT_INTERP`; é o teste
  correto quando não existe loader da glibc para invocar.
- **NixOS/Nix e imutabilidade.** A imagem `nixos/nix` fornece o Nix CLI em
  container; a libc vem do Nix store com uma revisão fixa do Nixpkgs. A
  imutabilidade do `/nix/store` não muda o resultado por si só — ajuda a
  reprodutibilidade. Na prática o loader fica em
  `<store>/lib/ld-linux-x86-64.so.2`; usa-se o caminho estável `/nix-loader`
  dentro da imagem, sem alterar o ELF.

## Regra do gerador oficial

`gen_data.py` contém a flag e gera a senha; ele **não** faz parte da entrega.
- Não existe no diretório de trabalho e não está versionado (`git ls-files`).
- `.dockerignore` impede que entre no contexto de build mesmo que exista local.
- `tests/test_p6.py` falha se algum módulo de `src/` importar `gen_data` ou se
  qualquer `Dockerfile` usar base sem digest.
- Os hashes do binário (`out/p6/matriz.tsv`) comprovam que todas as linhas usaram
  o mesmo ELF auditado: `925510065b1cd97c53bb6f46b64fbf9fe5a039aa892d6f5609e200e2c74d726a`.

## Limitações

A comparação com o ELF original é feita por **stdout**, pois o estado interno
vive em buffers de `sprintf` e não é observável pelo processo pai. O estado
completo (status, aceitação, flag) é comparado entre o emulador P3 e o modelo
P2. A equivalência vale para as 71 entradas testadas e para os ambientes acima;
não é prova para todas as entradas possíveis nem para versões futuras de libc.
Nenhuma modificação foi aplicada ao binário: o trabalho é engenharia reversa e
recuperação de uma entrada aceita.
