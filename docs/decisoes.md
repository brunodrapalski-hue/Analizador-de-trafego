# Decisões técnicas

Cada decisão registra o contexto, a escolha, a justificativa e o custo aceito (formato inspirado em *Architecture Decision Records*).

| ID | Tema | Decisão |
|---|---|---|
| D1 | Ambiente | Linux (WSL2) + Docker Engine |
| D2 | Linguagem e versões | Python 3.13, Scapy 2.7.0 |
| D3 | Fontes de pacotes | Captura ao vivo **e** leitura de `.pcap` |
| D4 | Rede e privilégios do container | `network_mode: host` + `NET_RAW` |
| D5 | Banco de dados | SQLite em volume |
| D6 | Escopo de pacotes | IPv4 e IPv6; não-IP descartado e contado |
| D7 | Classificação de protocolo | Pelo número de protocolo do cabeçalho IP |
| D8 | Tamanho do pacote | Tamanho do frame completo |
| D9 | "Mais tráfego" | Top 5 por pacotes **e** por bytes |
| D10 | Privacidade | Somente metadados |
| D11 | Gravação | Em lotes, com gravação garantida ao encerrar |
| D12 | Interface | Linha de comando com tabelas |

---

### D1 — Linux (WSL2) + Docker Engine

- **Contexto:** a captura exige acesso às interfaces de rede. No Windows, o Docker Desktop executa os containers em uma VM e não enxerga as placas físicas; o modo `host` tem limitações conhecidas nesse ambiente.
- **Decisão:** desenvolver e executar em Ubuntu (WSL2) com Docker Engine nativo.
- **Justificativa:** comportamento real de Linux, igual ao de um servidor; sem licenças comerciais.
- **Custo aceito:** no WSL2 a captura ocorre na interface virtual `eth0` do WSL, não na placa física do Windows.

### D2 — Python 3.13 e Scapy 2.7.0

- **Contexto:** o desafio prefere Python e sugere Scapy. Havia versões mais novas do Python disponíveis.
- **Decisão:** Python 3.13 (imagem `python:3.13-slim`) com Scapy 2.7.0.
- **Justificativa:** as versões foram escolhidas pela **matriz de suporte oficial**: 3.13 é a versão mais recente declarada como suportada pelo Scapy. Dependências com versão fixada garantem builds reproduzíveis.
- **Custo aceito:** não usar a versão mais recente do Python até que o Scapy declare suporte.

### D3 — Captura ao vivo e leitura de `.pcap`

- **Contexto:** o avaliador pode executar em um ambiente onde a captura ao vivo não é possível ou não gera tráfego representativo.
- **Decisão:** oferecer `--iface` (requisito) e `--pcap` (reprodutibilidade), ambos pelo mesmo `PacketCollector`.
- **Justificativa:** a demonstração funciona em qualquer máquina e os resultados são determinísticos — o que é validado com o `.pcap` vale para a captura ao vivo, pois o código é o mesmo.
- **Custo aceito:** nenhum relevante.

### D4 — `network_mode: host` + capacidades mínimas

- **Contexto:** capturar exige sockets brutos; a forma mais simples seria `privileged: true`.
- **Decisão:** rede do host e apenas a capacidade `NET_RAW`, necessária para abrir sockets brutos e realizar a captura.
- **Justificativa:** princípio do menor privilégio — o container não recebe acesso a dispositivos nem às demais capacidades administrativas.
- **Custo aceito:** o container compartilha a pilha de rede do host (necessário para capturar) e executa como root dentro do container (ver [seguranca.md](seguranca.md)).

### D5 — SQLite em volume

- **Contexto:** o desafio pede "um banco de dados", sem especificar qual.
- **Decisão:** SQLite (biblioteca padrão), arquivo em `./data`.
- **Justificativa:** zero configuração para o avaliador, SQL completo, transações e integridade referencial. Detalhes em [banco-de-dados.md](banco-de-dados.md).
- **Custo aceito:** um processo gravando por vez; evolução para PostgreSQL documentada.

### D6 — IPv4 e IPv6; não-IP descartado e contado

- **Contexto:** pacotes como ARP não têm endereço IP, protocolo IP nem os campos exigidos.
- **Decisão:** armazenar apenas IPv4 e IPv6; descartar os demais e registrar a quantidade em `packets_ignored`.
- **Justificativa:** comportamento definido e auditável — nenhum pacote some sem registro. Na amostra: 300 pacotes = 284 IP + 16 não-IP.
- **Custo aceito:** estatísticas não incluem tráfego de camada 2.

### D7 — Protocolo pelo número IP

- **Contexto:** é preciso um critério único e verificável para "protocolo".
- **Decisão:** usar o campo `proto` (IPv4) ou `nh` (IPv6): 6 = TCP, 17 = UDP, 1 = ICMP, 58 = ICMPv6, demais = `OTHER`. O número original é gravado em `protocol_num`.
- **Justificativa:** padrão IANA, determinístico e simples de conferir no Wireshark.
- **Custo aceito:** IPv6 com cabeçalhos de extensão é classificado pelo primeiro cabeçalho.

### D8 — Tamanho do frame completo

- **Contexto:** "tamanho do pacote" pode ser o frame inteiro ou apenas o datagrama IP.
- **Decisão:** bytes do frame completo — `len(pacote)` na captura ao vivo e o tamanho original (`wirelen`) em arquivos `.pcap`, mesmo se a captura foi truncada.
- **Justificativa:** mesmo critério da coluna *Length* do Wireshark, permitindo validação independente.
- **Custo aceito:** inclui o cabeçalho de enlace (14 bytes em Ethernet).

### D9 — Top 5 por pacotes e por bytes

- **Contexto:** "IPs com mais tráfego" é ambíguo.
- **Decisão:** exibir os dois rankings para origem e destino.
- **Justificativa:** um IP pode enviar muitos pacotes pequenos e outro poucos pacotes grandes. Na amostra, `4.228.31.150` é o 2º por pacotes (41) e o 1º por bytes (589.329) — um download típico.
- **Custo aceito:** quatro tabelas em vez de duas.

### D10 — Somente metadados

- **Contexto:** o conteúdo dos pacotes pode conter dados pessoais ou sensíveis e não é necessário para as estatísticas.
- **Decisão:** gravar apenas horário, versão IP, IPs, protocolo e tamanho.
- **Justificativa:** minimização de dados (LGPD, art. 6º, III) e menor impacto em caso de vazamento do banco.
- **Custo aceito:** não é possível inspecionar conteúdo depois da captura (fora do escopo).

### D11 — Gravação em lote

- **Contexto:** gravar um pacote por transação é lento sob tráfego intenso.
- **Decisão:** acumular registros e gravar a cada 100 (`TRAFFIC_BATCH_SIZE`) em uma transação; o restante é gravado no encerramento, inclusive com Ctrl+C (`finally`).
- **Justificativa:** desempenho com atomicidade por lote e sem perda de dados na interrupção.
- **Custo aceito:** em caso de falha abrupta do processo (ex.: `kill -9`), até 99 pacotes em memória podem ser perdidos.

### D12 — Linha de comando com tabelas

- **Contexto:** o desafio pede exibir estatísticas; uma interface web aumentaria escopo e risco.
- **Decisão:** CLI com `argparse` (biblioteca padrão) e tabelas com `rich`; cálculo (`stats.py`) separado da apresentação (`report.py`).
- **Justificativa:** simples de executar em Docker, legível e fácil de estender para outros formatos (JSON, web) sem alterar o cálculo.
- **Custo aceito:** sem visualização gráfica.

---

## Decisões de engenharia complementares

| Tema | Decisão | Justificativa |
|---|---|---|
| Dockerfile multi-stage | Estágios `test` e `runtime` a partir de uma base comum | Ferramentas de teste não entram na imagem de execução |
| Remoção do pip na imagem final | `pip uninstall` no estágio `runtime` | Corrige 2 vulnerabilidades encontradas pelo Trivy e reduz a superfície de ataque |
| Testes com pacotes sintéticos + amostra real | Pacotes montados com Scapy e validação com `demo.pcap` | Casos isolados e determinísticos + validação do conjunto contra números conferidos |
| Horário em UTC | `datetime` com fuso UTC | Correlação de eventos sem ambiguidade |
| Código em inglês, documentação em português | Padrão da indústria para código; documentação para o público do processo | Consistência |
| Conventional Commits | `feat:`, `fix:`, `test:`, `docs:`, `ci:` | Histórico legível e rastreável |
