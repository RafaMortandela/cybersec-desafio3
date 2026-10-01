# P1 — Extração da tabela e disassembly da ISA implícita

**Responsável:** Rafaela Silva Ruis
**Entrega:** `src/extract.py`, `src/disasm.py`, `out/sprint.asm`, `out/sprint.json`

Esta seção documenta a primeira etapa da reprodução do desafio *Sprint* (Google CTF 2020): recuperar, a partir do binário, o programa que a máquina executa. O objetivo não é apenas "rodar um script", mas justificar por que a tabela de *format strings* é uma sequência de instruções e como cada uma é traduzida para uma forma legível.

## O que o binário faz

`sprint` é um ELF64 PIE, não *stripped*. No início, `main` reserva uma região com `mmap` e copia para ela o símbolo `M` (uma tabela de 0xf134 bytes) com `memcpy`. Em seguida lê a senha do usuário com `scanf("%255s", ...)` e entra em um laço. Cada iteração do laço faz, em essência, uma única chamada:

```
sprintf(OUT, *PC, "", 0, &PC, OUT, <registradores...>);
```

Três observações sustentam toda a análise:

1. O segundo argumento de `sprintf` é `*PC`, isto é, a *format string* apontada pelo "program counter". A tabela `M` é, portanto, um vetor de instruções, e `PC` caminha por ela.
2. `sprintf` devolve (e, mais importante, contabiliza internamente) o número de caracteres escritos. Esse contador é o acumulador da máquina.
3. A especificação C permite gravar o contador de volta na memória com a conversão `%n` — aqui na variante de 16 bits `%hn`. É assim que a máquina escreve em registradores e no próprio `PC`.

O laço termina quando `PC` atinge um valor sentinela (o fim da tabela); então o binário verifica uma posição fixa da região e, se estiver preenchida, imprime `Flag: %s`.

> **Cuidado de reprodução.** A instrução `%4$s` faz `sprintf` ler o *próprio* buffer de saída enquanto ainda o escreve — comportamento indefinido pela norma C. Na glibc alvo isso é determinístico e é justamente o mecanismo dos desvios condicionais. Por isso a regra do grupo: rodar **o binário original**, registrando a versão da glibc, e nunca inferir o comportamento a partir de uma recompilação. Ambiente auditado: `glibc 2.39` (Ubuntu). SHA-256 do binário em `sprint.sha256`.

## Passo 1 — Extrair a tabela `M`

`extract.py` faz o *parse* do ELF64 na mão (cabeçalho, *section headers*, `.symtab`/`.strtab`), sem depender de bibliotecas externas, e localiza o símbolo `M` pelo seu endereço virtual e tamanho. Como o binário não é *stripped*, o símbolo está presente e o recorte é exato; há um *fallback* por `.rodata` documentado para o caso *stripped*.

```
$ python3 src/extract.py sprint --out out/M.bin
símbolo M: vaddr=0x2020 file_offset=0x2020 size=61748 (0xf134)
```

A maior parte de `M` é composta de bytes nulos: são a memória de trabalho e a área do labirinto, preenchidas em tempo de execução. As instruções propriamente ditas ficam concentradas no início da tabela — 146 instruções reais e dois registros de dados em `0xf000` e `0xf102`, inicialmente incluídos na saída P1.

## Passo 2 — Do texto da biblioteca para a ISA

A tradução (o *lifting*) é o núcleo da minha contribuição. Cada *format string* é percorrida da esquerda para a direita, mantendo o **comprimento acumulado de forma simbólica**: uma constante mais uma combinação linear de registradores, tudo módulo 2¹⁶ (porque `%hn` grava 16 bits). As diretivas se traduzem assim:

| Diretiva | Efeito no acumulador |
|---|---|
| `%1$00038s` | soma a constante 38 (arg 1 é a string vazia `""`; só gera preenchimento) |
| `%1$*8$s` | soma o **valor** do registrador ligado ao argumento 8 (largura variável) |
| `%1$2s` | soma 2 (string curta usada como incremento pequeno) |
| `%c` | soma 1 |
| `%4$s` | soma o comprimento do buffer `OUT` (leitura do buffer de saída) |
| `%N$hn` | **grava** o acumulado atual no destino de índice `N` |

Como `%hn` escreve o valor no instante em que aparece, a ordem importa: uma mesma instrução pode gravar em vários destinos, cada um com o acumulado daquele ponto. Isso explica um padrão recorrente — por exemplo `%1$00038s%3$hn%1$65498s%9$hn`:

- `+38` → grava 38 no `PC`;
- `+65498` → o acumulado passa a `38 + 65498 = 65536 ≡ 0`, gravado em `r3`.

Ou seja, a instrução significa "`r3 = 0; PC = 38`". O complemento `65498 = 65536 − 38` é a técnica usada o tempo todo para zerar ou subtrair via *wrap-around* de 16 bits.

### Mapa de argumentos → registradores

Os índices `%N$` referenciam argumentos posicionais de `sprintf`. Para dar nomes aos registradores, reconstruí a montagem da chamada a partir da sequência de `push` em `main`. Cada slot de memória aparece **duas vezes** entre os argumentos: uma como valor (para largura variável `%*N$s`) e uma como ponteiro (para escrita `%N$hn`). Disso resulta o mapa:

- argumento 3 → `PC` (ponteiro para o *program counter*; toda instrução escreve nele);
- argumento 4 → `OUT` (buffer de saída; lido via `%4$s` nos desvios);
- argumentos ≥ 5 → `r(N) = (N − 3) // 2`, produzindo `r1, r2, …, r10`.

Este mapa é uma **hipótese de análise estática**. A validação em execução — confirmar que cada `r`_i_ corresponde de fato ao slot esperado — é refinada pela P2 e pela P3. A P3 compara resultados com P2 e a saída com o ELF; não compara estados internos do ELF passo a passo.

## Passo 3 — Disassembly e classificação

`disasm.py` aplica a acumulação simbólica a cada instrução e a classifica em quatro classes de *opcode*, deduzidas da assinatura (quais destinos recebem escrita, se há largura variável, se o buffer é lido):

- **MOV** — grava um imediato em um registrador (`r1 = 1`);
- **ALU** — grava em um registrador uma combinação de registradores/imediatos (`r5 = r4 + r3`, `r4 = r3 + 65535`, isto é `r3 − 1`);
- **JMP** — só atualiza o `PC` (fluxo sequencial ou salto incondicional, `PC = 430`);
- **BR** — desvio condicional: lê `OUT` e o alvo do `PC` depende do resultado (`PC = OUT + 384`).

```
$ python3 src/disasm.py out/M.bin --json out/sprint.json --txt out/sprint.asm
148 instrucoes decodificadas
por classe: {'MOV': 39, 'ALU': 61, 'BR': 21, 'JMP': 27}
```

Trecho do disassembly gerado (`out/sprint.asm`):

```
0x000000  MOV   PC = 38; r3 = 28672
0x000026  ALU   PC = 74; r2 = r2
0x00004a  MOV   PC = 108; r1 = 1
0x00006c  ALU   PC = 149; r2 = r2 + 2
...
0x00015b  BR    PC = OUT + 384
...
0x000315  JMP   PC = 430
0x00043a  ALU   PC = 1129; r4 = r3 + 65535
```

A saída em JSON (`out/sprint.json`) traz, para cada instrução, o *offset*, a *format string* crua, a classe e cada atribuição já na forma simbólica (constante + termos de registradores). Esse JSON é a interface que entrego para as etapas seguintes: P2 interpreta o campo raw; P3 decodifica diretamente as strings da memória extraída; P4 lê os dados do ELF. O mapa genérico de nomes acima não é uma ISA executável correta; o mapa concreto está no write-up P3.

## Contribuição própria (além dos write-ups públicos)

Os write-ups existentes (hexrabbit e jay-invariant) descrevem a solução, mas resolvem a máquina de forma majoritariamente manual/ad hoc. A contribuição desta etapa é um **disassembler reprodutível e sem dependências**: um extrator de ELF em Python puro, um *lifter* que recupera a semântica de cada `%hn` por acumulação simbólica módulo 2¹⁶, um mapa argumento→registrador derivado da análise do prólogo de `main`, e uma saída estruturada (JSON) reutilizável pelas demais frentes. Isso transforma "ler a format string e adivinhar" em um passo determinístico e auditável.

## Limitações e pontos a validar com P3

- O mapa argumento→registrador é estático; os nomes `r1..r10` devem ser confirmados em execução.
- Os alvos das instruções `BR` aparecem como `PC = OUT + k`; a condição concreta (o que `OUT` contém no momento do desvio) só se resolve no emulador.
- A fronteira entre código e dados na tabela é dada pelos terminadores `NUL`; a região do labirinto (toda nula em repouso) é corretamente ignorada, mas isso deve ser reconfirmado quando P4 reconstruir o labirinto.

## Referências

Ver `docs/referencias.md` (repositório oficial no *commit* fixado, write-ups arquivados no web.archive, e o artigo de Carlini et al., *Control-Flow Bending*, USENIX Security 2015, sobre *printf* como mecanismo Turing-completo).

## Atualização após P2 e P3

Os exemplos de disassembly acima preservam a notação inicial de P1. Os nomes r1..r10 são genéricos e não devem ser usados para execução. O mapa concreto inclui memória indireta, dptr e oito registradores r0..r7. A contagem de 148 inclui dois registros de dados; há 146 instruções reais. P3 resolve os desvios como JNZ do byte baixo.
