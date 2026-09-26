# Decisões técnicas

Cada decisão registra a escolha, o motivo e o custo aceito.

| ID | Tema | Decisão |
|---|---|---|
| D1 | Ambiente | Linux (ou WSL2) com Docker |
| D2 | Versões | Python 3.13 e Scapy 2.7.0 |
| D3 | Fontes de pacotes | Captura ao vivo e leitura de `.pcap` |
| D4 | Rede e privilégios | `network_mode: host`, `NET_RAW` declarada, root |
| D5 | Banco | SQLite em volume |
| D6 | Escopo | IPv4 e IPv6; não-IP descartado e contado |
| D7 | Protocolo | Número do protocolo no cabeçalho IP |
| D8 | Tamanho | Frame completo |
| D9 | "Mais tráfego" | Top 5 por pacotes e por bytes |
| D10 | Dados gravados | Somente metadados |
| D11 | Gravação | Em lotes, com gravação do restante no encerramento |
| D12 | Interface | CLI com tabelas no terminal |
| D13 | Verificações | Quality gate e scan da imagem no CI |

---

### D1 — Linux (ou WSL2) com Docker

- **Decisão:** executar em Linux; no Windows, dentro do WSL2.
- **Por quê:** a captura precisa das interfaces de rede do host. No Docker Desktop, os containers rodam em uma VM e não enxergam as placas físicas.
- **Custo:** no WSL2, a captura ocorre na interface virtual do WSL (normalmente `eth0`). Ela recebe o tráfego gerado no próprio WSL, não o de todo o Windows.

### D2 — Python 3.13 e Scapy 2.7.0

- **Decisão:** imagem `python:3.13-slim` e dependências com versão fixada em `requirements*.txt`.
- **Por quê:** Python é a linguagem preferencial do desafio e Scapy é a biblioteca sugerida. A versão 3.13 é a mais recente que o Scapy 2.7.0 declara como suportada.
- **Custo:** não usar a versão mais recente do Python.

### D3 — Captura ao vivo e leitura de `.pcap`

- **Decisão:** `capture --iface` (o requisito) e `capture --pcap`. As duas fontes alimentam o mesmo `PacketCollector`.
- **Por quê:** o tráfego ao vivo muda a cada execução. Um `.pcap` é uma entrada fixa: os resultados podem ser conferidos no Wireshark e usados em testes. Como parser, persistência e estatísticas são os mesmos, validar com o arquivo também valida o processamento da captura ao vivo.
- **Custo:** `--count`, `--duration` e `--filter` valem só para a captura ao vivo. Com `--pcap`, são recusados com erro.

### D4 — Rede do host e privilégios do container

- **Decisão:**
  - `network_mode: host`;
  - `cap_add: NET_RAW`, declarada explicitamente;
  - sem `privileged`;
  - sem `NET_ADMIN`;
  - o processo roda como root dentro do container.
- **Por quê:** sem a rede do host, o container só vê a própria interface virtual. Capturar exige socket bruto (`NET_RAW`, que já faz parte do conjunto padrão do Docker; declarar deixa a necessidade explícita). `NET_ADMIN` não é necessário: a captura com filtro BPF funciona sem ele.
- **Custo:**
  - O container mantém o conjunto padrão de capabilities do Docker, e não apenas `NET_RAW`.
  - Ele compartilha a pilha de rede do host, embora não abra portas nem escute conexões.
  - Roda como root.
- **Evolução possível:** `cap_drop: [ALL]` com `cap_add: [NET_RAW]` e um usuário não-root com *file capabilities* no interpretador. Isso exige testar as permissões do volume `./data`.

### D5 — SQLite em volume

- **Decisão:** SQLite (biblioteca padrão do Python), arquivo `data/traffic.db` em volume.
- **Por quê:** não exige serviço de banco, usuário nem senha, e oferece SQL, transações e chaves estrangeiras. Detalhes em [banco-de-dados.md](banco-de-dados.md).
- **Custo:** um processo gravando por vez. Para vários sensores simultâneos, PostgreSQL seria a evolução, com adaptação de `storage.py` e `stats.py`.

### D6 — IPv4 e IPv6; não-IP descartado e contado

- **Decisão:** gravar apenas pacotes IPv4 e IPv6. Os demais frames (ex.: ARP) são contados em `packets_ignored`.
- **Por quê:** frames sem IP não têm os campos pedidos, mas continuam aparecendo no total capturado. Na amostra, são 300 frames = 284 IP + 16 não-IP.
- **Custo:** as estatísticas não detalham o tráfego de camada 2.

### D7 — Protocolo pelo número IP

- **Decisão:** usar o campo `proto` (IPv4) ou `nh` (IPv6): 6 = TCP, 17 = UDP, 1 = ICMP, 58 = ICMPv6, e os demais = `OTHER`. O número original fica em `protocol_num`.
- **Por quê:** é um critério único e fácil de conferir no Wireshark.
- **Custo:** IPv6 com cabeçalho de extensão é classificado pelo primeiro cabeçalho. Por exemplo, Hop-by-Hop aparece como `OTHER`.

### D8 — Tamanho do frame completo

- **Decisão:** registrar os bytes do frame completo: `len(pacote)` ao vivo e `wirelen` (tamanho original) em `.pcap`.
- **Por quê:** é o mesmo valor da coluna *Length* do Wireshark, o que permite validar de forma independente.
- **Custo:** o tamanho inclui o cabeçalho de enlace (14 bytes em Ethernet). Com offload de segmentação (GRO na recepção, TSO/GSO no envio), a captura vê segmentos TCP agregados, maiores que o MTU. Na amostra, 37 frames TCP passam de 1.514 bytes, e o maior tem 64.146 bytes. É o mesmo valor que o Wireshark mostra.

### D9 — Top 5 por pacotes e por bytes

- **Decisão:** exibir, para origem e para destino, um ranking por quantidade de pacotes e outro por bytes. Empates são desfeitos pela outra métrica e depois pelo IP.
- **Por quê:** "mais tráfego" é ambíguo. Na amostra, `4.228.31.150` é o 2º em pacotes (41) e o 1º em bytes (589.329), o perfil de um download.
- **Custo:** quatro tabelas em vez de duas.

### D10 — Somente metadados

- **Decisão:** gravar horário, versão IP, IPs, protocolo e tamanho. O payload não é lido para armazenamento nem gravado.
- **Por quê:** as estatísticas não precisam do conteúdo, e isso reduz a exposição caso o banco seja compartilhado. Endereços IP ainda podem identificar pessoas: a captura deve ser feita só em redes autorizadas, e o banco não é versionado (`.gitignore`).
- **Custo:** não é possível inspecionar o conteúdo depois da captura.

### D11 — Gravação em lotes

- **Decisão:** acumular registros e gravar a cada `TRAFFIC_BATCH_SIZE` (padrão 100) em uma transação. O restante é gravado no encerramento, no `finally` da captura.
- **Por quê:** uma transação por pacote é lenta sob tráfego intenso. Por lote, a gravação é atômica.
- **Custo:** no fim por `--count`, `--duration` ou Ctrl+C, nada se perde. Se o processo for morto por sinal (ex.: `kill`, `kill -9` ou `docker stop`), o lote em memória (até 99 pacotes, com o padrão) se perde e a sessão fica sem horário de término.

### D12 — CLI com tabelas

- **Decisão:** `argparse` (biblioteca padrão) e tabelas com `rich`. O cálculo (`stats.py`) fica separado da apresentação (`report.py`).
- **Por quê:** simples de executar em Docker e legível no terminal. Uma interface web aumentaria o escopo sem necessidade.
- **Custo:** sem visualização gráfica.

### D13 — Quality gate e scan da imagem

- **Decisão:**
  - `scripts/check.sh` executa ruff (lint e formatação), pytest, bandit e pip-audit, o mesmo script localmente e no CI.
  - O CI também faz o build da imagem de execução e a analisa com Trivy.
- **Por quê:** a mesma verificação roda em qualquer máquina. No CI, as actions são fixadas por SHA e o workflow tem permissão apenas de leitura.
- **Política do Trivy:** um relatório com HIGH e CRITICAL, só para visibilidade, e um gate que falha o build apenas com CRITICAL **com correção disponível**. Bloquear por achados sem correção impediria a entrega sem reduzir o risco.
- **Resultado:**
  - O primeiro scan apontou 2 HIGH corrigíveis (`msgpack` e `setuptools`), ambos embutidos no pip. O pip só é necessário no build e foi removido da imagem de execução ([antes](security/trivy-report-before-fix.txt), [depois](security/trivy-report.txt)).
  - Restam 45 HIGH em pacotes do Debian da imagem base, sem correção publicada, e 0 CRITICAL. A imagem não está livre de vulnerabilidades. Esses achados são acompanhados a cada execução do CI e somem ao atualizar a imagem base quando houver correção.
- **Custo:** a imagem base não é fixada por digest, então a contagem do Trivy pode mudar ao longo do tempo.
