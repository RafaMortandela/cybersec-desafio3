# P6: ambiente isolado e reproduzivel para o binario Sprint.
#
# Uso (ambiente de referencia, Ubuntu 24.04 / glibc 2.39):
#   docker build --platform linux/amd64 -t sprint-p6:ref-2.39 -f docker/Dockerfile .
#   docker run --rm -i --platform linux/amd64 sprint-p6:ref-2.39 \
#     /lib64/ld-linux-x86-64.so.2 /sprint < out/maze_path.txt
#
# A entrada nao precisa ser montada: o solver P4 regenera a rota a partir do
# proprio ELF, e a matriz do P6 usa src/validate.py com --image-binary /sprint.
#
# O parametro BASE_IMAGE permite montar as outras linhas da matriz sem
# duplicar o arquivo. A glibc observada e impressa em build e em run, para
# que o resultado possa ser conferido em vez de confiado no nome da tag.
#
# A solucao nao usa gen_data.py em nenhum momento: a senha e reconstruida a
# partir do proprio ELF por src/solve_maze.py. O gerador oficial do desafio
# contem a flag e fica fora do repositorio entregue.

ARG BASE_IMAGE=ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
FROM --platform=linux/amd64 ${BASE_IMAGE}

# Pacotes adicionais opcionais por linha da matriz, instalados pela familia
# do gerenciador de pacotes da base.
ARG EXTRA_PKGS=
RUN set -eu; \
    if [ -n "$EXTRA_PKGS" ]; then \
        if command -v apt-get >/dev/null 2>&1; then \
            export DEBIAN_FRONTEND=noninteractive; \
            apt-get update; \
            apt-get install -y --no-install-recommends $EXTRA_PKGS; \
            rm -rf /var/lib/apt/lists/*; \
        elif command -v apk >/dev/null 2>&1; then \
            apk add --no-cache $EXTRA_PKGS; \
        fi; \
    fi

# Toolchain minimo: a imagem oficial traz apenas o runtime. Precisamos de
# getconf (para registrar a libc), python3 (para o emulador P3 e o solver P4
# quando a matriz compara as tres pontas) e coreutils para o getent/loader.
RUN set -eu; \
    if command -v apt-get >/dev/null 2>&1; then \
        export DEBIAN_FRONTEND=noninteractive; \
        apt-get update; \
        apt-get install -y --no-install-recommends python3 ca-certificates; \
        rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
        apk add --no-cache python3; \
    fi

# Registra a libc efetiva no log de build. Em imagens musl isso imprime
# "musl", o que ja sinaliza que o ELF original (ligado para glibc) nao roda.
RUN set -eu; \
    printf 'sprint-p6 base: %s\n' "$(cat /etc/os-release 2>/dev/null | grep -E '^PRETTY_NAME=' || echo 'desconhecida')"; \
    printf 'sprint-p6 libc: %s\n' "$(getconf GNU_LIBC_VERSION 2>/dev/null || echo 'musl ou ausente')"; \
    printf 'sprint-p6 loader: %s\n' "$(ls /lib64/ld-linux-x86-64.so.2 /lib/ld-linux-x86-64.so.2 2>/dev/null | tr '\n' ' ' || echo 'nenhuma em /lib64 ou /lib')"

# O binario entra assado na imagem em vez de montado pelo host. Isso remove
# uma classe inteira de falso negativo: em hosts com SELinux em modo Enforcing
# (Fedora, RHEL) o bind mount de um arquivo em $HOME e negado e o ELF falha
# com rc=127 "cannot open shared object file: Permission denied" em TODAS as
# linhas da matriz, o que parece divergencia de libc mas nao e.
#
# O bit de execucao e liberado para permitir tambem a execucao direta, usada na
# linha musl, em que o kernel precisa resolver o PT_INTERP do proprio ELF.
ARG BINARY=sprint
COPY --chmod=0555 ${BINARY} /sprint
# O hash e conferido no build: se o binario nao for o perfil auditado, a imagem
# nao e construida. Isso torna o digest da imagem um atestado do binario.
ARG SPRINT_SHA256=925510065b1cd97c53bb6f46b64fbf9fe5a039aa892d6f5609e200e2c74d726a
RUN set -eu; \
    got="$(sha256sum /sprint | cut -d' ' -f1)"; \
    printf 'sprint-p6 binario: %s\n' "$got"; \
    if [ "$got" != "$SPRINT_SHA256" ]; then \
        echo "ERRO: hash do binario difere do perfil auditado" >&2; \
        echo "  esperado: $SPRINT_SHA256" >&2; \
        echo "  obtido:   $got" >&2; \
        exit 1; \
    fi

WORKDIR /work