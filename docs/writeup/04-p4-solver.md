# P4 — Reconstrução e solução do labirinto

O solver está em `src/solve_maze.py`. Ele extrai o símbolo `M` do ELF original pela rotina de P1 (`src/extract.py`); não usa dados do gerador oficial nem incorpora a senha publicada nos write-ups.

## Dados e regra de passagem

Na primeira fase, a VM marca 0, 1 e os números compostos em `0x7000 + 2*n`. Assim, o byte em `M[0xf000 + posição]` é o índice de um número: a célula é **livre se esse número é primo**. São 256 posições, organizadas em 16 linhas de 16 colunas. O ponto inicial vem de `M[0xf100] = 0x11`.

Os nove bytes de `M[0xf103:0xf10c]` são os negativos módulo 256 das posições obrigatórias. A VM só avança o contador quando o movimento chega ao checkpoint *atual*; por isso, passar por um checkpoint futuro não o cumpre antecipadamente. As posições calculadas, em ordem, são `0x7d`, `0xff`, `0x51`, `0xb7`, `0x53`, `0x3f`, `0xf1`, `0x75`, `0x1f`. Cada movimento é `u=-16`, `r=+1`, `d=+16` ou `l=-1`, sem atravessar as bordas da grade. A entrada precisa ter exatamente 254 caracteres.

## Busca

A BFS mantém `(posição, índice do próximo checkpoint)`. Ela expande apenas vizinhos livres e incrementa o índice ao alcançar o ponto exigido. O primeiro estado com índice 9 dá uma rota mínima que atravessa os nove pontos na ordem correta. O solver a percorre de novo para validar limites, paredes e checkpoints, e recusa o resultado se seu comprimento diferir dos 254 caracteres exigidos pelo binário. A grade com a rota está em `out/maze_map.txt`: `S` é início, `1`–`9` são checkpoints, `#` parede, `*` rota e `.` célula livre.

## Reprodução e evidência

```bash
python3 src/solve_maze.py sprint --path-out out/maze_path.txt --map-out out/maze_map.txt
getconf GNU_LIBC_VERSION
sha256sum -c sprint.sha256
/lib64/ld-linux-x86-64.so.2 ./sprint < out/maze_path.txt
```

Nesta execução, o solver gerou **254 movimentos**; `sha256sum` respondeu `sprint: OK`, `getconf` respondeu `glibc 2.39` e o binário imprimiu `Flag: CTF{n0w_ev3n_pr1n7f_1s_7ur1ng_c0mpl3te}`. A loader é usada porque o arquivo `sprint` neste checkout não tem permissão de execução. A leitura de `%4$s` sobre o próprio buffer de `sprintf` é comportamento indefinido, portanto essa execução não comprova que uma recompilação ou outra libc produzirá o mesmo resultado.

As regras de grade 16×16, crivo, início, checkpoints em ordem e 254 caracteres foram conferidas nos [write-ups de jay-invariant](https://tilde.town/~jay-invariant/sprint.html) e [hexrabbit](https://blog.hexrabbit.io/2020/08/25/Google-CTF-2020-sprint-Writeup/). Os bytes e a rota entregues acima foram derivados do ELF presente neste repositório.
