# Matriz de rastreabilidade

Cada requisito do desafio ligado à implementação, à forma de verificação e à evidência.

| # | Requisito do desafio | Implementação | Verificação | Evidência |
|---|---|---|---|---|
| R1 | Capturar pacotes de uma interface especificada | `app/capture.py` → `capture_live()` | `capture --iface eth0 --count 100` | [03-captura-ao-vivo.txt](evidencias/03-captura-ao-vivo.txt) |
| R2 | Usar biblioteca adequada (ex.: Scapy) | Scapy 2.7.0 (`sniff`, `PcapReader`) | `requirements.txt` | — |
| R3 | Capturar IP de origem, IP de destino, protocolo e tamanho | `app/parser.py` → `PacketRecord` | `tests/test_parser.py` (8 testes) | [quality-report.txt](security/quality-report.txt) |
| R4 | Número total de pacotes capturados | `app/stats.py` → `TOTALS_QUERY` | `test_totals_*`, `test_demo_pcap_statistics` | [01-estatisticas-demo-pcap.txt](evidencias/01-estatisticas-demo-pcap.txt) |
| R5 | Número de pacotes por protocolo | `app/stats.py` → `PROTOCOL_QUERY` | `test_packets_by_protocol` | [01-estatisticas-demo-pcap.txt](evidencias/01-estatisticas-demo-pcap.txt) |
| R6 | Top 5 IPs de origem com mais tráfego | `app/stats.py` → `TOP_QUERIES` (pacotes e bytes) | `test_top_sources_differ_by_packets_and_bytes`, `test_top_is_limited_to_five` | [01-estatisticas-demo-pcap.txt](evidencias/01-estatisticas-demo-pcap.txt) |
| R7 | Top 5 IPs de destino com mais tráfego | `app/stats.py` → `TOP_QUERIES` (pacotes e bytes) | `test_top_destinations` | [01-estatisticas-demo-pcap.txt](evidencias/01-estatisticas-demo-pcap.txt) |
| R8 | Armazenar os pacotes em banco de dados | `app/storage.py` (SQLite) | `tests/test_storage.py` (5 testes) | [02-sessoes.txt](evidencias/02-sessoes.txt) |
| R9 | Linguagem preferencialmente Python | Python 3.13 | `Dockerfile` | — |
| R10 | Executar em Docker | `Dockerfile` + `docker-compose.yml` | `docker compose run --rm analyzer ...` | todas as evidências |
| R11 | Documentação: configurar, executar e usar | [README.md](../README.md) | Ensaio: clonar e seguir apenas o README | — |
| R12 | Justificar escolhas, schema e informações do script | [decisoes.md](decisoes.md), [banco-de-dados.md](banco-de-dados.md), [arquitetura.md](arquitetura.md) | Revisão | — |

## Verificações adicionais (além do pedido)

| Item | Onde | Evidência |
|---|---|---|
| Tratamento de erros amigável | `app/cli.py` | [04-erro-interface.txt](evidencias/04-erro-interface.txt) |
| Portão de qualidade (lint, testes, SAST, dependências) | `scripts/check.sh` | [quality-report.txt](security/quality-report.txt) |
| Scan de vulnerabilidades da imagem | Trivy | [trivy-report.txt](security/trivy-report.txt) |
| Integração contínua | `.github/workflows/ci.yml` | Aba *Actions* do repositório |

## Números de referência — `samples/demo.pcap`

Valores de referência da amostra, verificados pelos testes `test_demo_pcap_*`:

| Métrica | Valor |
|---|---|
| Pacotes no arquivo | 300 |
| IP armazenados / não-IP ignorados | 284 / 16 |
| TCP / UDP / ICMP | 234 / 30 / 20 |
| Top 1 origem por pacotes | 172.19.40.48 (146) |
| Top 1 destino por pacotes | 172.19.40.48 (116) |

## Como regenerar as evidências

```bash
mkdir -p docs/evidencias
export COLUMNS=120
docker compose run --rm -T -e COLUMNS analyzer --db /tmp/demo.db capture --pcap samples/demo.pcap > docs/evidencias/01-estatisticas-demo-pcap.txt 2>&1
docker compose run --rm -T -e COLUMNS analyzer sessions > docs/evidencias/02-sessoes.txt 2>&1
docker compose run --rm -T -e COLUMNS analyzer stats --session 2 > docs/evidencias/03-captura-ao-vivo.txt 2>&1
docker compose run --rm -T -e COLUMNS analyzer capture --iface eth9 > docs/evidencias/04-erro-interface.txt 2>&1
```

A evidência 01 usa um banco temporário dentro do container (`/tmp/demo.db`), então o resultado é sempre o da sessão 1, idêntico a cada execução. As evidências 02 e 03 refletem o banco local `data/traffic.db`.
