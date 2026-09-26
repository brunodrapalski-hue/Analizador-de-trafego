# Guia de validação

Roteiro para reproduzir e validar a aplicação: comando, resultado esperado e o que cada etapa comprova. Todos os comandos são executados na raiz do repositório, em Linux ou no WSL2.

A referência numérica é `samples/demo.pcap`. A captura ao vivo varia com o ambiente e serve para comprovar que a captura funciona, não para comparar números.

## 1. Pré-requisitos e build

É preciso ter Git, Docker e Docker Compose instalados. Python e as bibliotecas ficam dentro da imagem.

```bash
git clone https://github.com/brunodrapalski-hue/Analizador-de-trafego.git
cd Analizador-de-trafego
docker compose build
```

Esperado: o build termina sem erro. `docker compose run --rm analyzer --help` lista os comandos `capture`, `stats` e `sessions`.

## 2. PCAP de referência

```bash
docker compose run --rm analyzer capture --pcap samples/demo.pcap
```

Esperado (saída completa em [evidencias/01](evidencias/01-estatisticas-demo-pcap.txt)):

| Resumo | Valor |
|---|---:|
| Total packets captured | 300 |
| IP packets stored | 284 |
| Non-IP packets ignored | 16 |
| Total bytes (IP) | 659.108 |

| Protocolo | Pacotes | % | Bytes |
|---|---:|---:|---:|
| TCP | 234 | 82,4% | 652.944 |
| UDP | 30 | 10,6% | 4.204 |
| ICMP | 20 | 7,0% | 1.960 |

| # | Origem por pacotes | Origem por bytes | Destino por pacotes | Destino por bytes |
|---|---|---|---|---|
| 1 | 172.19.40.48 (146) | 4.228.31.150 (589.329) | 172.19.40.48 (116) | 172.19.40.48 (636.402) |
| 2 | 4.228.31.150 (41) | 142.251.155.119 (29.438) | 4.228.31.150 (45) | 20.184.175.6 (6.934) |
| 3 | 172.19.32.1 (20) | 172.19.40.48 (19.222) | 108.158.137.127 (24) | 4.228.31.150 (3.722) |
| 4 | 142.251.155.119 (18) | 20.184.175.6 (8.032) | 142.251.155.119 (18) | 239.255.255.250 (2.666) |
| 5 | 108.158.137.127 (12) | 104.20.23.154 (6.058) | 108.158.137.57 (18) | 108.158.137.127 (2.052) |

**Como ler o resultado:**

- **300 = 284 + 16:** os 16 frames não-IP (ARP) são contados, mas não viram linha em `packets`. O percentual por protocolo é calculado sobre os 284 pacotes IP.
- **UDP inclui IPv6:** 2 dos 30 pacotes UDP são IPv6 (mDNS).
- **Empate no destino:** na 4ª e na 5ª posição há 18 pacotes cada. O desempate é por bytes (1.972 × 1.539).
- **Frames grandes:** alguns frames passam de 1.514 bytes (o maior tem 64.146). Isso vem do offload de segmentação na captura original (ver D8 em [decisoes.md](decisoes.md)).

**Conferência independente no Wireshark:**

| Filtro | Frames |
|---|---:|
| `ip or ipv6` | 284 |
| `arp` | 16 |
| `tcp` | 234 |
| `udp` | 30 |
| `icmp` | 20 |

Em `Statistics > Endpoints > IPv4`, as colunas Tx (origem) e Rx (destino), em pacotes e bytes, correspondem aos rankings.

As contagens principais (300, 284, 16, TCP, UDP, ICMP e o 1º colocado em pacotes) são verificadas por testes automatizados. Os valores em bytes e os demais rankings foram conferidos manualmente.

## 3. Captura ao vivo

Identifique a interface. No WSL2 normalmente é `eth0`:

```bash
ip -br link
```

Capture por 30 segundos e gere tráfego em outro terminal durante esse tempo:

```bash
docker compose run --rm analyzer capture --iface eth0 --duration 30
```

```bash
ping -c 10 1.1.1.1        # em outro terminal
```

Esperado: após 30 s, a sessão é encerrada e o relatório é exibido no mesmo formato. O ICMP do `ping` deve aparecer entre os protocolos. Os números variam a cada execução. Exemplo real: [evidencias/03](evidencias/03-captura-ao-vivo.txt), com 100 frames = 94 IP + 6 não-IP.

Outras formas de encerrar e filtrar:

| Comando | Comportamento |
|---|---|
| `--count 100` | Para após 100 frames que passem pelo filtro, IP ou não-IP. Sem tráfego, fica aguardando. |
| `--filter "icmp"` | Filtro BPF, a mesma sintaxe do tcpdump. Só os frames que passam pelo filtro são contados. |
| Sem `--count` e sem `--duration` | Captura até Ctrl+C. O lote pendente é gravado e a sessão é encerrada normalmente. |

## 4. Persistência e consultas

```bash
docker compose run --rm analyzer sessions               # lista as sessões
docker compose run --rm analyzer stats --session 1      # uma sessão, sem nova captura
docker compose run --rm analyzer stats                  # todas as sessões somadas
```

**O que comprova:**

- O banco `data/traffic.db` fica no host e sobrevive ao `--rm`, que remove só o container.
- `sessions` mostra origem (`pcap:demo.pcap`, `iface:eth0`), filtro, início e fim (UTC) e contadores. Exemplo: [evidencias/02](evidencias/02-sessoes.txt).
- `stats` sem `--session` soma todo o histórico. Se o `demo.pcap` for processado duas vezes, o total será 600. Para comparar com a referência, use `stats --session N`, ou comece com um banco vazio (seção 9).

## 5. Tratamento de erros

| Comando | Resultado esperado | Saída |
|---|---|---:|
| `capture --iface eth9` | `ERROR: Interface 'eth9' not found. Available: lo, eth0, ...` ([evidencias/04](evidencias/04-erro-interface.txt)) | 1 |
| `capture --pcap samples/inexistente.pcap` | `ERROR: pcap file not found: samples/inexistente.pcap` | 1 |
| `capture --pcap samples/demo.pcap --count 5` | `ERROR: --count can only be used with --iface.` | 1 |
| `stats --session 99` | `ERROR: Session 99 not found.` | 1 |
| `capture --iface eth0 --count 0` (ou `--duration 0`) | `argument -c/--count: must be greater than zero` | 2 |
| `TRAFFIC_BATCH_SIZE=0` em qualquer `capture` | `ERROR: TRAFFIC_BATCH_SIZE must be greater than zero.` | 1 |

Nesses casos nenhuma sessão é criada. Com `docker compose run`, variáveis de ambiente são passadas com `-e`, por exemplo `docker compose run --rm -e TRAFFIC_BATCH_SIZE=0 analyzer capture --pcap samples/demo.pcap`.

## 6. Quality gate e CI

```bash
docker compose run --rm -T --build quality     # ruff, formatação, pytest, bandit, pip-audit
docker compose run --rm --build tests          # só os testes
```

Esperado ([quality-report.txt](security/quality-report.txt)):

- `All checks passed!` (ruff);
- `13 files already formatted`;
- `41 passed`;
- `No issues identified.` (bandit);
- `No known vulnerabilities found` (pip-audit);
- ao final, `==> All checks passed.`

O script para na primeira falha (`set -e`).

O CI (`.github/workflows/ci.yml`) roda a cada push na `main` e em pull requests:

1. o mesmo quality gate;
2. o build da imagem `analyzer`;
3. um relatório do Trivy (HIGH e CRITICAL);
4. um gate que falha só com CRITICAL corrigível.

A situação atual da imagem é 45 HIGH do Debian sem correção e 0 CRITICAL ([trivy-report.txt](security/trivy-report.txt)). A política está em D13, em [decisoes.md](decisoes.md).

## 7. Requisito → validação

| Requisito do desafio | Implementação | Teste automatizado | Validação manual / evidência |
|---|---|---|---|
| Capturar de uma interface especificada | `capture_live()` em `capture.py` | `test_live_capture_rejects_unknown_interface` | Seção 3; [evidencias/03](evidencias/03-captura-ao-vivo.txt) |
| Biblioteca adequada | Scapy (`sniff`, `PcapReader`) | — | `requirements.txt` |
| IP de origem, destino, protocolo e tamanho | `parse_packet()` → `PacketRecord` | `tests/test_parser.py` (8 casos) | Seção 2 |
| Total de pacotes | `TOTALS_QUERY` + `IGNORED_QUERY` | `test_totals_*`, `test_demo_pcap_statistics` | Seção 2; [evidencias/01](evidencias/01-estatisticas-demo-pcap.txt) |
| Pacotes por protocolo | `PROTOCOL_QUERY` | `test_packets_by_protocol` | Seção 2 |
| Top 5 origem | `TOP_QUERIES` (pacotes e bytes) | `test_top_sources_differ_by_packets_and_bytes`, `test_top_is_limited_to_five` | Seção 2 |
| Top 5 destino | `TOP_QUERIES` (pacotes e bytes) | `test_top_destinations` | Seção 2 |
| Armazenar em banco | `storage.py` (SQLite) | `tests/test_storage.py` (5 casos) | Seção 4; [evidencias/02](evidencias/02-sessoes.txt) |
| Python + Docker | `Dockerfile`, `docker-compose.yml` | Executados no container (seção 6) | Seção 1 |

A captura ao vivo com tráfego real não tem teste automatizado, porque depende do ambiente. Ela foi validada manualmente (evidência 03).

## 8. Regenerar as evidências

```bash
export COLUMNS=120
docker compose run --rm -T -e COLUMNS analyzer --db /tmp/demo.db capture --pcap samples/demo.pcap > docs/evidencias/01-estatisticas-demo-pcap.txt 2>&1
docker compose run --rm -T -e COLUMNS analyzer sessions > docs/evidencias/02-sessoes.txt 2>&1
docker compose run --rm -T -e COLUMNS analyzer stats --session 2 > docs/evidencias/03-captura-ao-vivo.txt 2>&1
docker compose run --rm -T -e COLUMNS analyzer capture --iface eth9 > docs/evidencias/04-erro-interface.txt 2>&1
```

A evidência 01 usa um banco temporário dentro do container, então sempre sai como a sessão 1. As evidências 02 e 03 dependem do histórico em `data/traffic.db`.

## 9. Troubleshooting

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `Interface '...' not found` | O nome da interface é outro nesta máquina | Use um nome listado na própria mensagem ou em `ip -br link` |
| `ERROR: [Errno 1] Operation not permitted` na captura ao vivo | O processo não tem a capability `NET_RAW` (ex.: `cap_drop`, Docker rootless ou execução fora do container sem root) | Execute pelo `docker compose` do projeto, que roda como root com `NET_RAW` |
| A captura ao vivo termina com 0 pacotes | Não havia tráfego na interface, ou o filtro excluiu tudo | Gere tráfego (`ping`) durante a captura; revise o `--filter` |
| `--count` não termina | O número de frames ainda não foi atingido | Use `--duration` ou Ctrl+C |
| `pcap file not found` | Comando fora da raiz do repositório, ou caminho errado | Rode na raiz; o caminho é relativo ao container (`samples/...`) |
| Números maiores que a referência | `stats` sem `--session` soma todas as sessões | Use `stats --session N` ou limpe o banco |
| `Not a supported capture file` | O arquivo não é uma captura válida (pcap ou pcapng) | Confira o arquivo; reexporte pelo Wireshark |

## 10. Limpeza

Os containers já são removidos pelo `--rm`. Para apagar o histórico de capturas:

```bash
rm -f data/traffic.db        # use sudo se a pasta data/ tiver sido criada pelo Docker (dono: root)
```

O schema é recriado automaticamente na próxima execução.
