# P10 — Write-up Técnico e Metodologia

Este documento consolida o raciocínio metodológico por trás da nossa engenharia reversa do desafio Sprint (Google CTF 2020)[cite: 5], justificando as decisões arquiteturais da equipe e detalhando as contribuições originais que superam as soluções públicas existentes.

## Metodologia Justificada

Em vez de depender exclusivamente de análise manual em depuradores, optamos por construir um pipeline formal e automatizado, dividido nas seguintes etapas:

- **Extração e Representação Intermediária:** O binário utiliza chamadas `sprintf` para executar instruções armazenadas em uma tabela `M`[cite: 5]. O script `extract.py` faz o parse manual do ELF64, sem bibliotecas externas, para extrair essa tabela[cite: 5]. Em seguida, o lifter traduz a string de formatação (que possui comportamento indefinido em C) em uma acumulação simbólica módulo 2¹⁶[cite: 5]. Isso converte a lógica obscura em operações legíveis (MOV, ALU, JMP, BR), exportadas estruturadamente em `sprint.json` e `sprint.asm`[cite: 5].
- **Emulação Isolada:** Para evitar o comportamento indefinido (UB) gerado pela leitura e escrita simultânea do buffer com `%4$s`[cite: 5], construímos um emulador próprio (`src/emulate.py`)[cite: 6]. Ele executa as primitivas lendo as strings diretamente da memória extraída, gerenciando seu próprio mapeamento de registradores (r0-r7, dptr, PC), sem realizar chamadas reais ao `sprintf`[cite: 6].   
- **Reconstrução e Busca:** O `solve_maze.py` reconstrói a matriz 16x16 a partir dos dados do ELF[cite: 7]. A regra de passagem foi modelada formalmente: a VM utiliza um crivo para marcar números compostos, de forma que uma célula só é livre se o seu índice corresponder a um número primo[cite: 7]. Utilizamos uma Busca em Largura (BFS) para encontrar uma rota que cruze 9 checkpoints obrigatórios em ordem exata, resultando em uma entrada de 254 movimentos[cite: 7].
- **Validação de Ambiente:** Em vez de assumir que o binário funciona universalmente, modelamos a execução ponta a ponta contra múltiplas distribuições Linux, isolando os testes em contêineres Docker com digests fixos[cite: 8].


## O que acrescentamos aos materiais públicos

Enquanto os write-ups públicos conhecidos (como os de hexrabbit e jay-invariant)[cite: 7] descrevem a solução de forma majoritariamente manual e ad-hoc, nosso projeto introduz as seguintes contribuições formais:

- **Desacoplamento e Automação Total:** Criamos um ecossistema sem dependências externas. O desassemblador, o emulador e o solver são ferramentas independentes. Diferente de soluções que aproveitam o gerador oficial do desafio, nós garantimos a exclusão estrita do arquivo `gen_data.py` (bloqueado via `.dockerignore` e testes), provando que a solução deriva 100% do ELF[cite: 8].
- **Matriz de Comportamento de C Runtimes (glibc vs musl):** Write-ups públicos costumam focar em um único ambiente. Nós testamos o binário contra 7 ambientes diferentes (Ubuntu 20.04/22.04/24.04, Debian 12, Arch Linux, NixOS e Alpine)[cite: 8]. Comprovamos que o comportamento indefinido do `sprintf` é estável nas versões da `glibc` 2.31 até 2.44, produzindo saídas idênticas[cite: 8]. Também demonstramos e documentamos que o binário falha no Alpine (musl) não por erro de lógica da VM, mas pela ausência do loader `/lib64/ld-linux-x86-64.so.2`[cite: 8].
- **Correção de Falsos Negativos de Execução:** Identificamos que execuções locais em sistemas com SELinux Enforcing (como Fedora) geram falhas de permissão ao usar bind mounts (`-v`) no Docker[cite: 8]. Corrigimos isso incorporando o binário diretamente nas imagens fixadas da etapa P6, tornando o digest da imagem um atestado de integridade do ambiente[cite: 8].

## Reprodutibilidade e Artefatos

Todo o pipeline gera artefatos auditáveis para comprovar a validade da execução:

- **Artefatos de Análise:** A abstração do binário é salva em `out/sprint.json` e `out/sprint.asm`[cite: 5].
- **Artefatos de Solução:** O mapa do labirinto renderizado e o caminho validado são gerados em `out/maze_map.txt` e `out/maze_path.txt`[cite: 7].
- **Validação Cruzada:** A corretude do emulador é assegurada por 18 testes unitários[cite: 6]. Além disso, 71 entradas (incluindo rotas válidas, parciais e sequências aleatórias) são validadas diferencialmente: o estado interno do emulador (P3) é comparado ao modelo (P2), e a saída emulada é comparada ao stdout do binário real executado no ambiente de referência[cite: 6, 8].

As instruções exatas de linha de comando para reproduzir cada uma dessas etapas e gerar os artefatos estão documentadas no README principal do repositório.