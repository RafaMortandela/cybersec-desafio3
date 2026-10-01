# P3 — Emulador próprio da ISA Sprint

## Objetivo e contribuição

A P3 implementa `src/emulate.py`, um interpretador que executa as instruções recuperadas do Sprint sem chamar `sprintf`. Diferentemente do P2, ele não substitui o programa por algoritmos conhecidos de crivo, percurso e decifração: mantém memória, registradores e PC e executa uma instrução por vez. O crivo e a flag aparecem como efeitos da execução do código extraído.

A extração reutiliza o parser ELF do P1. O emulador lê as strings diretamente da memória inicial extraída do binário e possui decodificador próprio. Não importa `lift.py`, `p2_model.py`, `solve_maze.py` ou o gerador oficial. Isso evita executar os nomes genéricos incorretos do disassembly P1. O perfil é limitado ao hash original registrado no projeto; não é um interpretador geral de printf.

## Estado e mapa de argumentos

Os ponteiros nativos são representados por offsets em relação à base da memória da VM. No original, PC e dptr começam nessa base; no emulador, ambos começam em zero. Os oito registradores numéricos começam em zero.

| Argumento | Leitura ou escrita |
|---|---|
| 1 | String vazia usada para produzir preenchimento |
| 2 | Zero usado como byte NUL no desvio |
| 3 | Ponteiro para PC, destino de `%3$hn` |
| 4 | Buffer de saída usado no padrão de desvio |
| 5 | Word de 16 bits lido em dptr |
| 6 | Valor de dptr em largura variável; ponteiro para memória em `%6$hn` |
| 7 | Ponteiro para dptr, destino de `%7$hn` |
| 8, 10, …, 22 | Valores de r0, r1, …, r7 |
| 9, 11, …, 23 | Ponteiros para r0, r1, …, r7 |

A memória é um `bytearray` de 65.537 bytes, cobrindo offsets de 16 bits e o segundo byte de um word iniciado em `0xffff`. Esse é o espaço necessário ao perfil, não uma reprodução dos 64 MiB de mmap do original. Words são little-endian e podem estar em endereços ímpares. A entrada modela `%255s` em locale C: ignora whitespace ASCII inicial, lê no máximo 255 bytes até whitespace e grava um terminador NUL em `0xe000`. NUL embutido permanece na memória e encerra a leitura posterior como string.

## Execução das primitivas

Cada passo busca a string terminada em NUL em PC. O decodificador aceita os padrões presentes no Sprint e rejeita diretivas desconhecidas. A cache usa a string completa como chave; a busca continua sendo feita na memória atual, de modo que uma modificação do código não deixa uma instrução antiga vinculada ao endereço.

Nos formatos lineares, a contagem começa em zero. `%1$Ns` soma N e `%1$*K$s` soma o valor do argumento K, que no perfil é não negativo. `%K$hn` escreve a contagem módulo 65.536 no destino K. As escritas ocorrem na ordem das diretivas. Todos os argumentos de valor e os ponteiros para memória são capturados antes da instrução, assim como na preparação da chamada original. Escrever em um registrador ou em dptr não altera os argumentos já capturados para essa mesma instrução.

O desvio reconhece o padrão `%K$c%1$As%2$c%4$s%1$Bs%3$hn`. O byte de `%K$c` decide se o buffer começa em NUL. Os destinos são `(2+A+B) mod 65536` para byte baixo zero e `(3+2*A+B) mod 65536` para byte baixo não zero. Portanto, 256 toma o mesmo ramo que zero. No desvio em `0x015b`, os destinos são `0x0180` e `0x0324`.

Essa regra modela o efeito recuperado da implementação alvo, sem criar um buffer de saída e sem reproduzir o comportamento indefinido em Python. PC igual a `0xfffe` encerra a execução. Um limite configurável de instruções permite interromper loops. O status é r7, a flag é a string em `0xe800`, e a API devolve também PC, dptr, registradores e contagem de instruções.

## Uso

Execute na raiz do projeto, com Python 3.9 ou superior, sem dependências externas:

```bash
python3 src/emulate.py --input out/maze_path.txt
python3 src/emulate.py --input out/maze_path.txt --json
python3 src/emulate.py --input out/maze_path.txt --trace out/p3_trace.jsonl
python3 -m unittest discover -s tests -v
```

Também aceita entrada por stdin e `--binary` para indicar o original em outra pasta. A CLI retorna 0 para entrada aceita, 1 para rejeitada e 2 para erro de arquivo, perfil, decodificação ou limite. Esses códigos são uma interface da P3: o ELF original retorna 0 também quando rejeita a senha. A opção trace grava o estado antes de cada instrução, para uso pelos responsáveis por P5.

## Evidência de validação

Em 1 de outubro de 2026, a suíte completa executou 18 testes com sucesso em Linux x86-64, glibc 2.39. O SHA-256 do original permaneceu `925510065b1cd97c53bb6f46b64fbf9fe5a039aa892d6f5609e200e2c74d726a`.

A rota do P4 foi aceita após 19.234 instruções, com PC final `0xfffe`, status zero e flag `CTF{n0w_ev3n_pr1n7f_1s_7ur1ng_c0mpl3te}`. Os 256 words produzidos pelo crivo foram comparados com um teste independente de primalidade por divisão.

Os testes P3 verificam truncamento de 16 bits, words desalinhados e no último endereço, argumentos capturados antes das escritas, desvio por byte baixo, formato desconhecido, limite de execução e trace. Outras 62 entradas foram comparadas com P2 quanto a status, aceitação e flag. Incluem rota correta, comprimentos incorretos, todos os status de rejeição de 1 a 5, NUL, whitespace, byte não ASCII, mutações da rota e sequências aleatórias com semente fixa.

As mesmas 62 entradas foram executadas no ELF original pela loader glibc e produziram stdout idêntico ao esperado pela P3, sem stderr e com término normal. Esse teste é ignorado automaticamente fora de Linux x86-64 com a loader esperada. A comparação com o ELF cobre a saída, não o estado interno por instrução. A validação P5 posteriormente ampliou o conjunto para 71 entradas, e a matriz de versões de glibc está documentada no [write-up P6](06-p6-ambiente-glibc.md). A instrumentação de estados internos do ELF não está implementada.

## Integração e limites

P1 fornece a extração; P2 oferece uma interpretação estruturada independente para comparação; P3 executa as primitivas; P4 fornece a rota. A P3 preserva o teste linear de posição da VM, sem adicionar bloqueio geométrico de coluna. P4 deliberadamente usa vizinhos geométricos mais restritivos, e sua rota foi aceita pelo original.

A validação comprova equivalência nas entradas testadas e no ambiente registrado. Não comprova equivalência para todas as entradas possíveis ou todas as bibliotecas C. Nenhuma modificação de segurança foi aplicada ao binário original: o trabalho é engenharia reversa e recuperação de uma entrada aceita.
