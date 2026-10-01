# P6: usa o Nix store com uma revisao imutavel do Nixpkgs.
# Esta imagem nixos/nix fornece o Nix CLI em container; nao inicializa o
# sistema operacional NixOS. A libc usada pelo ELF e a glibc empacotada pela
# revisao pinada do Nixpkgs.
#
# Build:
#   docker build --platform linux/amd64 -f docker/Dockerfile.nix \
#     -t sprint-p6:nixpkgs-glibc-2.40 .
# Execucao diferencial:
#   python3 src/validate.py --backend docker \
#     --image sprint-p6:nixpkgs-glibc-2.40 --image-binary /sprint \
#     --image-loader /nix-loader --report out/p6/validate-nixpkgs.json

FROM --platform=linux/amd64 nixos/nix@sha256:a09d508c2e46d3a4c7205ff3fa0d506d626a5a966c31e879df7efe737e22f003

# Nixpkgs nixos-24.11 resolvido para este commit. Nao usar a branch movel no
# build: esta revisao fornece glibc 2.40 e e consultavel pelo seu hash.
ARG NIXPKGS_REV=50ab793786d9de88ee30ec4e4c24fb4236fc2674
ARG SPRINT_SHA256=925510065b1cd97c53bb6f46b64fbf9fe5a039aa892d6f5609e200e2c74d726a

COPY --chmod=0555 sprint /sprint

RUN set -eu; \
    got="$(sha256sum /sprint | cut -d' ' -f1)"; \
    printf 'sprint-p6 binario: %s\n' "$got"; \
    if [ "$got" != "$SPRINT_SHA256" ]; then \
        echo "ERRO: hash do binario difere do perfil auditado" >&2; \
        exit 1; \
    fi; \
    ref="github:NixOS/nixpkgs/$NIXPKGS_REV"; \
    glibc="$(nix --extra-experimental-features 'nix-command flakes' eval --raw "$ref#glibc.outPath")"; \
    glibc_bin="$(nix --extra-experimental-features 'nix-command flakes' build --no-link --print-out-paths "$ref#glibc.bin")"; \
    version="$("$glibc_bin/bin/getconf" GNU_LIBC_VERSION)"; \
    printf 'sprint-p6 nixpkgs: %s\n' "$NIXPKGS_REV"; \
    printf 'sprint-p6 libc: %s\n' "$version"; \
    printf 'sprint-p6 glibc store path: %s\n' "$glibc"; \
    test -x "$glibc/lib/ld-linux-x86-64.so.2"; \
    ln -s "$glibc/lib/ld-linux-x86-64.so.2" /nix-loader; \
    ln -sf "$glibc_bin/bin/getconf" /root/.nix-profile/bin/getconf

WORKDIR /work
