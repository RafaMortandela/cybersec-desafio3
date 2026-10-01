# Revisão de coesão dos materiais

A referência de escopo é a reunião de 30 de setembro: P3 é um emulador próprio, não a etapa de testes atribuída a Eduardo em reuniões anteriores. A entrega implementa esse escopo mais recente.

| Material | Constatação e tratamento |
|---|---|
| Notas de 30 de setembro | P1–P4 formam uma sequência coerente. P3 estava ausente e foi implementada. |
| Notas de 16 de setembro | A frase sobre resolver a vulnerabilidade não descreve o Sprint atual. A atividade recupera a lógica e a entrada aceita, sem corrigir o ELF. |
| Código e README | P2 já corrigia o mapa genérico do P1. P3 usa decodificação própria e o mesmo mapa concreto. README atualizado com execução da P3. |
| Write-up P1 | Caminhos corrigidos; contagem real e limitações do mapa inicial esclarecidas. Removida a promessa de comparação de estados internos que ainda não existe. |
| Write-up P4 | Esclarecida a diferença entre limites geométricos da BFS e o teste linear da VM. |
| Slides | Rota de 254 movimentos, checkpoints em ordem, flag e glibc 2.39 confirmados nesta execução. Acrescentar a contribuição P3 na apresentação. |
| Referências | Corrigida a atribuição de argumentos posicionais a ISO C: essa sintaxe é POSIX. Links externos e afirmações históricas não foram auditados nesta revisão. |

## Texto sugerido para apresentar a P3

“Implementamos um emulador que executa as instruções extraídas sem usar sprintf. Ele mantém memória, oito registradores e o contador de programa, reproduzindo escritas de 16 bits e desvios pelo byte baixo. A rota do solver executou 19.234 instruções e recuperou a mesma flag. Comparamos 62 entradas com o modelo estruturado e com a saída do binário original na glibc 2.39.”

O PDF dos slides e o DOCX das notas foram preservados. Esta revisão e o write-up P3 fornecem os ajustes a incorporar. P5 e P6 ainda precisam concluir suas entregas próprias, especialmente a matriz de glibc e eventual comparação de estados internos.
