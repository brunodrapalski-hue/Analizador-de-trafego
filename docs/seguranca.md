# Segurança e privacidade

Uma ferramenta de captura lida com dados de rede, que podem incluir dados pessoais, e precisa de privilégios elevados para funcionar. Este documento registra os controles adotados, a análise de ameaças e os riscos residuais aceitos.

## Uso autorizado

Capture tráfego **somente** em redes e equipamentos sob sua responsabilidade ou com autorização expressa. A interceptação não autorizada de comunicações pode configurar crime e violar políticas internas.

## Controles implementados

| Controle | Implementação | Referência |
|---|---|---|
| Minimização de dados | Só metadados são gravados; o conteúdo dos pacotes nunca é lido para armazenamento | D10, `app/parser.py` |
| Menor privilégio no container | Apenas `NET_RAW` e `NET_ADMIN`; sem `privileged` | D4, `docker-compose.yml` |
| Amostras somente leitura | Volume `./samples` montado com `:ro` | `docker-compose.yml` |
| Prevenção de SQL injection | Consultas estáticas e parametrizadas (`?`); nenhum SQL montado com texto | `app/storage.py`, `app/stats.py` |
| Integridade dos dados | Chave estrangeira, `CHECK`, `NOT NULL` e transações | [banco-de-dados.md](banco-de-dados.md) |
| Trilha de auditoria | Cada captura registra origem, filtro, início, fim e contadores | tabela `capture_sessions` |
| Imagem enxuta | Multi-stage: sem ferramentas de teste e sem pip na imagem final | `Dockerfile` |
| Dependências fixadas | Versões exatas em `requirements*.txt` | builds reproduzíveis |
| Dados fora do repositório | `data/` e `*.db` no `.gitignore` | `.gitignore` |
| Análise estática (SAST) | bandit + regras de segurança do ruff (`S`) | `scripts/check.sh` |
| Auditoria de dependências | pip-audit | `scripts/check.sh` |
| Scan da imagem | Trivy (relatório + bloqueio de CRITICAL corrigível) | `.github/workflows/ci.yml` |
| Cadeia de suprimentos no CI | Actions fixadas por SHA de commit; `permissions: contents: read` | `.github/workflows/ci.yml` |

## Privacidade (LGPD)

- **Dado pessoal envolvido:** endereços IP podem identificar pessoas e são tratados como dado pessoal.
- **Finalidade:** análise estatística de tráfego para fins técnicos.
- **Minimização:** somente os campos exigidos pelo desafio mais horário e versão IP; nenhum conteúdo de comunicação.
- **Armazenamento:** local, no host que executa a ferramenta; o banco não é versionado.
- **Retenção sugerida:** manter o banco apenas pelo tempo necessário à análise e excluir `data/traffic.db` ao final.
- **Amostra publicada:** `samples/demo.pcap` foi gerado com tráfego controlado, em rede interna do WSL (IPs 172.19.x), sem tráfego HTTP em texto claro, e revisado antes da publicação.

## Modelo de ameaças (STRIDE)

| Categoria | Ameaça | Controle / tratamento |
|---|---|---|
| **S**poofing (falsificação) | Pacotes forjados distorcendo as estatísticas | Fora do escopo: a ferramenta registra o tráfego observado, sem autenticá-lo. Limitação documentada. |
| **T**ampering (adulteração) | Alteração do banco ou das amostras | Permissões do host sobre `./data`; `samples` somente leitura; restrições de integridade no banco |
| **R**epudiation (repúdio) | Não saber quando/como uma captura foi feita | Tabela `capture_sessions` com origem, filtro e horários UTC |
| **I**nformation disclosure (vazamento) | Exposição de dados de rede | Só metadados; banco local e fora do Git; retenção recomendada |
| **D**enial of service (negação de serviço) | Tráfego intenso esgotando memória ou disco | Processamento em fluxo (`store=False`, `PcapReader`), gravação em lote, limites `--count`/`--duration` e filtro BPF |
| **E**levation of privilege (elevação) | Abuso dos privilégios do container | Somente 2 capacidades; imagem sem pip; scan contínuo de vulnerabilidades |

## Análise de vulnerabilidades da imagem (Trivy)

| Momento | HIGH | CRITICAL | Observação |
|---|---|---|---|
| Primeiro scan | 47 | 0 | 45 no sistema base (Debian 13) + 2 em código embutido no pip (`msgpack`, `setuptools`) |
| Após correção | 45 | 0 | pip removido da imagem final; restam apenas achados do sistema base |

**Correção aplicada:** os 2 achados com correção disponível estavam em bibliotecas embutidas no `pip`, que só é necessário durante o build. O pip foi removido da imagem de execução, eliminando os achados e reduzindo a superfície de ataque. Relatório atual: [trivy-report.txt](security/trivy-report.txt).

## Registro de riscos residuais

| ID | Risco | Probabilidade | Impacto | Controles compensatórios | Decisão | Reavaliação |
|---|---|---|---|---|---|---|
| RR-01 | 45 vulnerabilidades HIGH em pacotes do Debian (ex.: `util-linux`, `acl`) **sem correção publicada** | Baixa | Médio | Os binários afetados (ex.: `mount`, `nsenter`) não são executados pela aplicação; o container não possui `SYS_ADMIN`; execução efêmera (`--rm`); exploração exige execução prévia de comandos dentro do container | **Aceitar** e monitorar | A cada build no CI; atualizar a imagem base quando houver correção |
| RR-02 | Container executa como root | Baixa | Médio | Capacidades limitadas a `NET_RAW`/`NET_ADMIN`; sem `privileged`; sem serviços expostos | **Aceitar** (captura exige sockets brutos) | Evolução: usuário não-root com *file capabilities* no interpretador |
| RR-03 | `network_mode: host` compartilha a pilha de rede do host | Baixa | Baixo | A aplicação não abre portas nem escuta conexões | **Aceitar** (necessário para capturar) | — |
| RR-04 | Banco contém IPs (dado pessoal) | Média | Médio | Somente metadados; armazenamento local; fora do Git; retenção recomendada | **Mitigar** com orientação de uso | Ao compartilhar resultados |

**Política do pipeline:** o build falha se houver vulnerabilidade **CRITICAL com correção disponível** (acionável). As demais são registradas no relatório e tratadas neste registro. Bloquear por vulnerabilidades sem correção impediria entregas sem reduzir o risco.

## Como reproduzir as verificações

```bash
# Lint, formatação, testes, bandit e pip-audit
docker compose run --rm -T --build quality | tee docs/security/quality-report.txt

# Scan da imagem de execução
docker compose build analyzer
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.74.0 \
  image --severity HIGH,CRITICAL traffic-analyzer:1.0.0 | tee docs/security/trivy-report.txt
```

O acesso ao `docker.sock` concede ao Trivy acesso ao Docker para ler a imagem; por isso é usada somente a imagem oficial com versão fixada.
