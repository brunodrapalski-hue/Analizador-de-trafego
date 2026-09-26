# Arquitetura

## Visão geral

A aplicação é uma ferramenta de linha de comando empacotada em Docker. Ela recebe pacotes de duas fontes possíveis — uma interface de rede ou um arquivo `.pcap` — e processa ambas pelo **mesmo pipeline**: normalização, gravação em lote no SQLite e cálculo de estatísticas via SQL.

```mermaid
flowchart TB
    U([Usuário / Avaliador]) -->|docker compose run| CLI

    subgraph Container["Container traffic-analyzer:1.0.0"]
        CLI[cli.py<br/>comandos capture, stats, sessions]
        CAP[capture.py<br/>PacketCollector]
        PAR[parser.py<br/>parse_packet]
        STO[storage.py<br/>Storage]
        STA[stats.py<br/>compute_stats]
        REP[report.py<br/>tabelas rich]
        CLI --> CAP --> PAR
        CAP --> STO
        CLI --> STA --> REP
    end

    NIC[Interface de rede<br/>eth0] -->|Scapy sniff| CAP
    PCAP[samples/*.pcap<br/>volume somente leitura] -->|PcapReader| CAP
    STO --> DB[(data/traffic.db<br/>volume persistente)]
    STA -->|consultas SQL| DB
```

## Responsabilidade de cada módulo

| Módulo | Responsabilidade | Não faz |
|---|---|---|
| `cli.py` | Interpreta comandos e argumentos, trata erros e define o código de saída | Não acessa pacotes nem SQL diretamente |
| `capture.py` | Obtém pacotes (ao vivo ou arquivo), aplica o lote e fecha a sessão | Não conhece o formato do banco |
| `parser.py` | Converte um pacote Scapy em `PacketRecord` imutável ou o descarta | Não grava nada |
| `storage.py` | Cria o schema, registra sessões e insere pacotes em transações | Não calcula estatísticas |
| `stats.py` | Calcula as estatísticas com consultas SQL parametrizadas | Não formata saída |
| `report.py` | Exibe estatísticas e sessões em tabelas | Não consulta o banco |
| `config.py` | Centraliza configurações com valores padrão e variáveis de ambiente | — |

A separação permite testar cada parte isoladamente e trocar uma camada sem afetar as demais (ex.: SQLite → PostgreSQL em `storage.py`, terminal → JSON em `report.py`).

## Fluxo de um pacote

```mermaid
flowchart TD
    A[Pacote recebido] --> B{Tem camada IPv4?}
    B -- sim --> D[versão 4, protocolo = campo proto]
    B -- não --> C{Tem camada IPv6?}
    C -- sim --> E[versão 6, protocolo = campo nh]
    C -- não --> F[Descartado e contado<br/>packets_ignored + 1]
    D --> G[Classifica: 6=TCP, 17=UDP,<br/>1=ICMP, 58=ICMPv6, outros=OTHER]
    E --> G
    G --> H[PacketRecord: horário UTC, IPs,<br/>protocolo, tamanho do frame]
    H --> I[Buffer]
    I --> J{Buffer >= 100?}
    J -- sim --> K[INSERT em lote<br/>uma transação]
    J -- não --> L[Aguarda próximo pacote]
```

## Sequência de uma captura

```mermaid
sequenceDiagram
    actor U as Usuário
    participant CLI as cli.py
    participant CAP as capture.py
    participant PRS as parser.py
    participant STO as storage.py
    participant DB as SQLite
    participant STA as stats.py

    U->>CLI: capture --iface eth0 --count 100
    CLI->>STO: abre banco (cria schema se necessário)
    CLI->>CAP: capture_live()
    CAP->>CAP: valida interface
    CAP->>STO: start_session()
    STO->>DB: INSERT capture_sessions
    loop cada pacote
        CAP->>PRS: parse_packet()
        PRS-->>CAP: PacketRecord ou None
        opt buffer cheio (100)
            CAP->>STO: insert_packets(lote)
            STO->>DB: INSERT ... (transação)
        end
    end
    Note over CAP: fim por count, duration ou Ctrl+C
    CAP->>STO: insert_packets(restante) + finish_session()
    STO->>DB: UPDATE capture_sessions
    CLI->>STA: compute_stats(sessão)
    STA->>DB: SELECT ... GROUP BY / ORDER BY / LIMIT 5
    STA-->>CLI: TrafficStats
    CLI-->>U: tabelas de estatísticas
```

## Implantação

```mermaid
flowchart TB
    subgraph Windows["Windows 11"]
        subgraph WSL["WSL2 — Ubuntu 24.04"]
            subgraph Docker["Docker Engine"]
                C["Container analyzer<br/>network_mode: host<br/>cap_add: NET_RAW"]
            end
            NIC[eth0 do WSL]
            V1[./data]
            V2[./samples]
        end
    end
    C ---|captura| NIC
    C ---|volume leitura/escrita| V1
    C ---|volume somente leitura| V2
```

| Item | Configuração | Motivo |
|---|---|---|
| Rede | `network_mode: host` | O container enxerga as interfaces reais do host para capturar |
| Privilégios | `cap_add: NET_RAW` | Capacidade necessária para sockets brutos; sem `NET_ADMIN` e sem `privileged` |
| Dados | `./data:/app/data` | O banco persiste entre execuções |
| Amostras | `./samples:/app/samples:ro` | Leitura de `.pcap` sem permissão de escrita |

## Imagens Docker (multi-stage)

| Estágio | Imagem | Conteúdo | Uso |
|---|---|---|---|
| `base` | — | Python 3.13 slim, tcpdump/libpcap, scapy, rich, código | Base comum |
| `test` | `traffic-analyzer-tests:1.0.0` | base + pytest, ruff, bandit, pip-audit, testes, amostra | Testes e portão de qualidade |
| `runtime` | `traffic-analyzer:1.0.0` | base **sem o pip** | Execução da aplicação |

A imagem de execução não contém ferramentas de teste nem o instalador de pacotes, reduzindo a superfície de ataque (ver [seguranca.md](seguranca.md)).
