#!/usr/bin/env python3
"""
extract.py  --  Extração da tabela de "instruções" (format strings) do binário Sprint.

Sprint (Google CTF 2020) implementa uma máquina virtual inteiramente dentro de
chamadas a sprintf(). O binário copia uma tabela contígua de format strings
(o símbolo `M`) para uma região mmap e a interpreta: cada format string é uma
"instrução" da ISA implícita. Este módulo localiza e recorta essa tabela.

Não depende de bibliotecas externas: faz o parse do ELF64 na mão (cabeçalho,
section headers, symtab, strtab) para achar o símbolo `M` e seu tamanho.
Se o símbolo não existir (binário stripped), há um fallback por heurística.

Uso:
    python3 extract.py ../sprint --out ../out/M.bin

Saída:
    - M.bin      : bytes crus da tabela
    - imprime endereço virtual, offset de arquivo e tamanho de `M`
"""
import argparse
import struct
import sys

ELF_MAGIC = b"\x7fELF"


class Elf64:
    """Parser mínimo de ELF64 little-endian, suficiente para o Sprint."""

    def __init__(self, data: bytes):
        if data[:4] != ELF_MAGIC:
            raise ValueError("não é um ELF")
        if data[4] != 2:
            raise ValueError("apenas ELF64 é suportado")
        if data[5] != 1:
            raise ValueError("apenas little-endian é suportado")
        self.data = data
        # e_shoff (offset da tabela de seções), e_shentsize, e_shnum, e_shstrndx
        self.e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        self.e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        self.e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        self.e_shstrndx = struct.unpack_from("<H", data, 0x3E)[0]
        self.sections = self._read_sections()

    def _read_sections(self):
        secs = []
        for i in range(self.e_shnum):
            off = self.e_shoff + i * self.e_shentsize
            (sh_name, sh_type, sh_flags, sh_addr, sh_offset,
             sh_size, sh_link, sh_info, sh_addralign,
             sh_entsize) = struct.unpack_from("<IIQQQQIIQQ", self.data, off)
            secs.append({
                "name_off": sh_name, "type": sh_type, "flags": sh_flags,
                "addr": sh_addr, "offset": sh_offset, "size": sh_size,
                "link": sh_link, "info": sh_info, "entsize": sh_entsize,
            })
        # resolve nomes de seção
        shstr = secs[self.e_shstrndx]
        base = shstr["offset"]
        for s in secs:
            s["name"] = self._cstr(base + s["name_off"])
        return secs

    def _cstr(self, off: int) -> str:
        end = self.data.index(b"\x00", off)
        return self.data[off:end].decode("latin-1")

    def section(self, name: str):
        for s in self.sections:
            if s["name"] == name:
                return s
        return None

    def symbols(self):
        """Itera (nome, valor, tamanho) da .symtab (ou .dynsym como fallback)."""
        symtab = self.section(".symtab") or self.section(".dynsym")
        if symtab is None:
            return
        strtab = self.sections[symtab["link"]]
        n = symtab["size"] // 24  # Elf64_Sym tem 24 bytes
        for i in range(n):
            off = symtab["offset"] + i * 24
            (st_name, st_info, st_other, st_shndx,
             st_value, st_size) = struct.unpack_from("<IBBHQQ", self.data, off)
            if st_name == 0:
                continue
            name = self._cstr(strtab["offset"] + st_name)
            yield name, st_value, st_size

    def vaddr_to_offset(self, vaddr: int) -> int:
        """Traduz endereço virtual em offset de arquivo usando as seções."""
        for s in self.sections:
            if s["addr"] <= vaddr < s["addr"] + s["size"] and s["type"] != 8:  # 8 = NOBITS
                return s["offset"] + (vaddr - s["addr"])
        raise ValueError(f"vaddr {hex(vaddr)} fora das seções carregadas")


def find_table(elf: Elf64):
    """Retorna (vaddr, file_offset, size) da tabela M."""
    for name, value, size in elf.symbols():
        if name == "M" and size > 0:
            return value, elf.vaddr_to_offset(value), size
    # Fallback (binário stripped): a tabela mora em .rodata e é a maior
    # sequência de format strings ("%1$" domina). Aqui devolvemos a .rodata
    # inteira e deixamos o disassembler recortar; documente essa limitação.
    ro = elf.section(".rodata")
    if ro is None:
        raise RuntimeError("símbolo M ausente e sem .rodata")
    sys.stderr.write("[aviso] símbolo M não encontrado; usando .rodata inteira\n")
    return ro["addr"], ro["offset"], ro["size"]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Extrai a tabela M do binário Sprint")
    ap.add_argument("binary", help="caminho para o binário sprint")
    ap.add_argument("--out", default="M.bin", help="arquivo de saída com os bytes de M")
    args = ap.parse_args(argv)

    data = open(args.binary, "rb").read()
    elf = Elf64(data)
    vaddr, foff, size = find_table(elf)
    table = data[foff:foff + size]
    open(args.out, "wb").write(table)

    print(f"símbolo M: vaddr={hex(vaddr)} file_offset={hex(foff)} size={size} ({hex(size)})")
    print(f"gravado {len(table)} bytes em {args.out}")
    # sanidade: contar quantos '%' e quantos terminadores nulos
    print(f"  '%' na tabela: {table.count(b'%')}   NUL: {table.count(0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
