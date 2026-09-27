# Guia de execução e validação

Passo a passo para preparar o ambiente, executar a aplicação e conferir o resultado de cada comando. Siga as etapas na ordem. Cada uma traz o objetivo, os comandos e o **resultado esperado**. 

A captura ao vivo varia com o ambiente: ela serve para comprovar o funcionamento da captura.

<br>

## Por onde começar

| Seu ambiente | Comece em |
|---|---|
| **Windows 10/11** | [Etapa 1 — Verificar e preparar o Windows](#etapa-1--verificar-e-preparar-o-windows) |
| **Linux com Docker Engine e Docker Compose** | [Etapa 2 — Verificar os pré-requisitos](#etapa-2--verificar-os-pré-requisitos) |

> **Por que WSL2 com Docker Engine, e não Docker Desktop?**  
> A captura ao vivo precisa enxergar uma interface de rede do ambiente Linux onde o tráfego de teste é gerado. Com o Docker Engine executado dentro do WSL2, o container utiliza a rede desse Linux e consegue capturar na interface `eth0` do WSL. Isso mantém identificação da interface, geração de tráfego, Docker e captura no mesmo contexto de rede. A decisão e o custo aceito estão detalhados em [docs/decisoes.md](decisoes.md).

---

<br>

## Etapa 1 — Verificar e preparar o Windows

**Objetivo:** identificar o que já está disponível na máquina e instalar somente os componentes necessários para executar e validar a aplicação.

A preparação do WSL2 e do Docker Engine é necessária apenas uma vez.

<br>

---

### 1.1 Verificar se o WSL2 já está disponível

Antes de instalar qualquer componente, abra o **PowerShell** e execute:

```powershell
wsl --status
wsl -l -v
```

O primeiro comando mostra o estado geral do WSL. O segundo lista as distribuições Linux instaladas e a versão utilizada por cada uma.

<br>

**Resultado esperado**, caso o Ubuntu 24.04 já esteja disponível no WSL2:

```text
  NAME            STATE           VERSION
* Ubuntu-24.04    Running         2
```

Se `Ubuntu-24.04` já aparecer com `VERSION` igual a `2`, o ambiente Linux necessário já está disponível. **Não reinstale o WSL nem o Ubuntu** e avance para a [Etapa 1.4](#14-verificar-git-e-docker-engine).

Se o Ubuntu 24.04 não estiver listado ou o WSL ainda não estiver disponível, continue para a próxima etapa.

> O objetivo desta verificação é evitar alterações desnecessárias em uma máquina que já possua parte do ambiente preparado.


<br>

### 1.2 Instalar o WSL2 com Ubuntu 24.04, se necessário

Esta etapa só é necessária se o Ubuntu 24.04 no WSL2 não tiver sido identificado na etapa anterior.

Abra o **PowerShell como administrador** e execute:

```powershell
wsl --install -d Ubuntu-24.04
```

<br>

**Resultado esperado:** mensagens de download e instalação. Dependendo do estado do Windows, pode ser solicitado reiniciar o computador.

> Se aparecer um erro relacionado à virtualização, verifique se o recurso de virtualização está habilitado na BIOS/UEFI do dispositivo e repita o comando.

<br>

### 1.3 Primeiro acesso ao Ubuntu

Após a instalação, abra `Ubuntu-24.04` pelo menu Iniciar.

Na primeira execução, o Ubuntu solicitará a criação de um nome de usuário e uma senha. Esses dados pertencem somente ao ambiente Linux e a senha será utilizada posteriormente pelo `sudo`.

<br>

**Resultado esperado:** um prompt semelhante a:

```text
usuario@computador:~$
```

> A partir daqui, os comandos da aplicação são executados no **terminal do Ubuntu**, exceto quando o guia indicar explicitamente o PowerShell.

<br>

### 1.4 Verificar Git e Docker Engine

Antes de instalar novos pacotes, verifique o que já está disponível no Ubuntu.

No **terminal do Ubuntu**, execute:

```bash
git --version
docker --version
docker compose version
systemctl is-active docker
```

<br>

**Resultado esperado**, caso o ambiente já esteja preparado:

| Comando | Resultado esperado |
|---|---|
| `git --version` | Exibe a versão instalada do Git |
| `docker --version` | Exibe a versão instalada do Docker |
| `docker compose version` | Exibe a versão do Docker Compose |
| `systemctl is-active docker` | `active` |

Se os quatro comandos responderem corretamente, não é necessário reinstalar Git ou Docker Engine. Avance para a [Etapa 2](#etapa-2--verificar-os-pré-requisitos).

**Só se algum componente não estiver disponível, continue para a próxima etapa.**

<br>

### 1.5 Instalar Git e Docker Engine no Ubuntu, se necessário

No **terminal do Ubuntu**, execute:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

<br>

**Resultado esperado:** os pacotes são instalados sem mensagens de erro.

### 1.6 Permitir o uso do Docker sem `sudo`

Adicione o usuário atual ao grupo `docker`:

```bash
sudo usermod -aG docker $USER
```

Para aplicar a alteração, encerre o WSL. No **PowerShell**, execute:

```powershell
wsl --shutdown
```

Abra novamente o Ubuntu e confira:

```bash
groups
systemctl is-active docker
```

<br>

**Resultado esperado:**

- `docker` aparece entre os grupos do usuário;
- o serviço Docker responde `active`.

A preparação inicial do Windows está concluída.

---

<br>

## Etapa 2 — Verificar os pré-requisitos

**Objetivo:** confirmar que Git, Docker Engine e Docker Compose estão funcionando antes de importar ou executar o projeto.

Esta etapa é o ponto comum para:

- Windows preparado pela Etapa 1;
- Linux que já possui Docker Engine e Docker Compose.

No **terminal Linux**, execute:

```bash
git --version
docker --version
docker compose version
docker run --rm hello-world
```
<br>

**Resultado esperado:**

| Comando | Saída esperada |
|---|---|
| `git --version` | `git version 2.x.x` |
| `docker --version` | `Docker version 2x.x.x, build ...` |
| `docker compose version` | `Docker Compose version v2.x.x` |
| `docker run --rm hello-world` | Contém `Hello from Docker!` |

Se os quatro comandos forem executados corretamente, o ambiente está pronto para importar o projeto.

> As dependências Python da aplicação não precisam ser instaladas no Ubuntu. Elas fazem parte das imagens Docker utilizadas pelo projeto.

---

<br>

## Etapa 3 — Importação do projeto

<br>
<br>
<br>
<br>
<br>
<br>







### 1.5 Usar o Docker sem `sudo`

```bash
sudo usermod -aG docker $USER
```

Em seguida, reinicie o WSL para aplicar a permissão. No **PowerShell**:

```powershell
wsl --shutdown
```

Agora no **Terminal do Ubuntu** novamente e confira:

```bash
groups
systemctl is-active docker
```
<br>

**Resultado esperado:** `docker` aparece na lista de grupos, e o serviço responde `active`.

---
<br>

## Etapa 2 — Verificar os pré-requisitos

Vamos confirmar que Git, Docker e Docker Compose funcionam. Fique tranquilo que toda as bibliotecas do projeto estarão dentro da imagem Docker na etapa de importação.

```bash
git --version
docker --version
docker compose version
docker run --rm hello-world
```

<br>

**Resultado esperado:**

| Comando | Saída (as versões podem variar) |
|---|---|
| `git --version` | `git version 2.x.x` |
| `docker --version` | `Docker version 2x.x.x, build ...` |
| `docker compose version` | `Docker Compose version v2.x.x` |
| `docker run --rm hello-world` | Contém `Hello from Docker!` |


---
<br>

## Etapa 3 — Importação do projeto

Iremos agora clonar o repositório. Por ser público não necessitará de nenhuma autenticação.

```bash
cd ~
git clone https://github.com/brunodrapalski-hue/Analizador-de-trafego.git
cd Analizador-de-trafego
ls
```

**Resultado esperado:** o `ls` lista, entre outros, `app/`, `docs/`, `samples/`, `tests/`, `Dockerfile`, `docker-compose.yml` e `README.md`.

> No WSL2, clone dentro da pasta do Linux (`~`), e não em `/mnt/c/...`. O acesso a arquivos do Windows pelo WSL é mais lento.

**Atenção!** Todos os comandos das próximas etapas serão executados nesta pasta, `cd ~/Analizador-de-trafego`.

---

<br>

## Etapa 4 — Construir a imagem

**Objetivo:** Gerar a imagem da aplicação as demais dependências.

```bash
docker compose build
docker image ls traffic-analyzer
docker compose run --rm analyzer --help
```

**Resultado esperado:**

- O build termina sem erro. Na primeira vez leva alguns minutos, porque baixa a imagem base.
- `docker image ls` mostra `traffic-analyzer` com a tag `1.0.0`.
- O `--help` mostra `usage: traffic-analyzer [-h] [--db DB] {capture,stats,sessions} ...`.

---

<br>

## Etapa 5 — Analisar o PCAP de referência

**Objetivo:** Agora vamos validar o pipeline completo (leitura → parser → SQLite → estatísticas) com uma entrada fixa afim de validação.

```bash
docker compose run --rm analyzer capture --pcap samples/demo.pcap
```

**Resultado esperado:** primeiro a linha `INFO: Session 1 finished: 284 packets stored, 16 non-IP packets ignored.`, e em seguida as tabelas abaixo. [evidencias/01](evidencias/01-estatisticas-demo-pcap.txt).

| Summary | Valor |
|---|---:|
| Total packets captured | 300 |
| IP packets stored | 284 |
| Non-IP packets ignored | 16 |
| Total bytes (IP) | 659,108 |

| Protocolo | Pacotes | % | Bytes |
|---|---:|---:|---:|
| TCP | 234 | 82.4% | 652,944 |
| UDP | 30 | 10.6% | 4,204 |
| ICMP | 20 | 7.0% | 1,960 |

| # | Origem por pacotes | Origem por bytes | Destino por pacotes | Destino por bytes |
|---|---|---|---|---|
| 1 | 172.19.40.48 (146) | 4.228.31.150 (589.329) | 172.19.40.48 (116) | 172.19.40.48 (636.402) |
| 2 | 4.228.31.150 (41) | 142.251.155.119 (29.438) | 4.228.31.150 (45) | 20.184.175.6 (6.934) |
| 3 | 172.19.32.1 (20) | 172.19.40.48 (19.222) | 108.158.137.127 (24) | 4.228.31.150 (3.722) |
| 4 | 142.251.155.119 (18) | 20.184.175.6 (8.032) | 142.251.155.119 (18) | 239.255.255.250 (2.666) |
| 5 | 108.158.137.127 (12) | 104.20.23.154 (6.058) | 108.158.137.57 (18) | 108.158.137.127 (2.052) |

**Como interpretar:**

- **300 = 284 + 16:** os 16 frames não-IP (ARP) são contados, mas não viram linha no banco. O percentual por protocolo é calculado sobre os 284 pacotes IP.
- **UDP inclui IPv6:** 2 dos 30 pacotes UDP são IPv6 (mDNS).
- **Empate no ranking:** na 4ª e na 5ª posição do destino há 18 pacotes cada. O desempate é por bytes (1.972 × 1.539).
- **Frames grandes:** alguns frames passam de 1.514 bytes (o maior tem 64.146). Isso vem do offload de segmentação na captura original (ver D8 em [decisoes.md](decisoes.md)).

**Conferência independente (opcional):** abra `samples/demo.pcap` no Wireshark. Os filtros `ip or ipv6`, `arp`, `tcp`, `udp` e `icmp` mostram 284, 16, 234, 30 e 20 frames. Em `Statistics > Endpoints > IPv4`, as colunas Tx (origem) e Rx (destino) correspondem aos rankings.

As contagens principais (300, 284, 16, TCP, UDP, ICMP e o 1º colocado em pacotes) também são verificadas por testes automatizados.

---

<br>

## Etapa 6 — Hora de Iniciar a Captura ao vivo

**Objetivo:** comprovar a captura em uma interface real do ambiente.

<br>

### 6.1 Identificar a interface

```bash
ip -br link
```

**Resultado esperado:** a lista de interfaces. No WSL2, a principal é `eth0`, com estado `UP`:

```text
lo               UNKNOWN        00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>
eth0             UP             00:15:5d:xx:xx:xx <BROADCAST,MULTICAST,UP,LOWER_UP>
docker0          DOWN           02:42:xx:xx:xx:xx <NO-CARRIER,BROADCAST,MULTICAST,UP>
```

Em Linux nativo, o nome costuma ser outro (ex.: `enp0s3`, `wlp2s0`). Nos comandos abaixo, troque `eth0` pelo nome da sua interface.

<br>

### 6.2 Capturar por 30 segundos gerando tráfego

Nesta etapa a proposta é realizar a captura e geração de trafego através de dois terminais **Ubuntu** (abertos em- cd ~/Analizador-de-trafego). Deixe ambos os terminais abertos.

No terminal 1 execute:

```bash
docker compose run --rm analyzer capture --iface eth0 --duration 30
```

**Resultado esperado:** a linha `INFO: Capturing on eth0 (press Ctrl+C to stop)...`, e o terminal fica aguardando.

Enquanto isso, no terminal 2:

```bash
ping -c 10 1.1.1.1
curl -s -o /dev/null https://github.com && echo OK
```

**Resultado esperado no terminal 1:** depois de 30 s, a captura termina sozinha, mostra `INFO: Session 2 finished: ...` e exibe as tabelas no mesmo formato da Etapa 5, com **ICMP** e os protocolos. Os números variam a cada execução. Exemplo real: [evidencias/03](evidencias/03-captura-ao-vivo.txt).

<br>

### 6.3 Outras formas de encerrar e filtrar (é opcional para explorar)

| Comando | Comportamento |
|---|---|
| `--count 100` | Para após 100 frames (pacotes) que passem pelo filtro, IP ou não-IP. Sem tráfego, fica aguardando. |
| `--duration 60` | Para após 60 (segundos) que passem pelo filtro, IP ou não-IP. sempre termina no tempo definido, com ou sem tráfego. |
| `--filter "icmp"` | Filtro BPF, com a mesma sintaxe do tcpdump. Só os frames que passam pelo filtro são contados. |
| Sem `--count` e sem `--duration` | Captura até Ctrl+C. Os pacotes coletados são gravados e o relatório é exibido. |

---

<br>

## Etapa 7 — Consultar os dados gravados

**Objetivo:** Comprovar que os dados ficam no banco e podem ser consultados sem uma nova captura.

```bash
docker compose run --rm analyzer sessions
docker compose run --rm analyzer stats --session 1
docker compose run --rm analyzer stats
```

**Resultado esperado:**

- `sessions` lista a sessão 1 (`pcap:demo.pcap`, 284 armazenados, 16 ignorados) e a sessão 2 (`iface:eth0`), com início e fim em UTC. Exemplo: [evidencias/02](evidencias/02-sessoes.txt).
- `stats --session 1` mostra exatamente os números da Etapa 5.
- `stats`, sem `--session`, soma todas as sessões. O total é maior que o da Etapa 5.

**O que comprova:** o banco `data/traffic.db` fica no host e sobrevive ao `--rm`, que remove só o container.

---

<br>

## Etapa — Testes e verificações de qualidade

**Objetivo:** executar a mesma verificação automatizada usada no CI.

```bash
docker compose run --rm -T --build quality
```

**Resultado esperado** (relatório salvo em [quality-report.txt](security/quality-report.txt)), nesta ordem:

| Verificação | Saída |
|---|---|
| ruff (lint) | `All checks passed!` |
| ruff (formatação) | `13 files already formatted` |
| pytest | `41 passed` |
| bandit | `No issues identified.` |
| pip-audit | `No known vulnerabilities found` |
| Final | `==> All checks passed.` |

O script para na primeira falha. O CI no GitHub Actions executa esse mesmo comando a cada push na `main` e em pull requests. Em seguida, faz o build da imagem e a analisa com Trivy: o build falha somente com vulnerabilidade CRITICAL corrigível. Hoje a imagem tem 45 HIGH do Debian, sem correção publicada, e 0 CRITICAL ([trivy-report.txt](security/trivy-report.txt)). A política está em D13, em [decisoes.md](decisoes.md).

---

<br>

## Etapa — Limpeza

Cada captura grava uma sessão nova no arquivo data/traffic.db, e esse arquivo continua existindo depois que o container termina. Essa etapa serve para zerar o banco de dados e deixar o ambiente como estava antes do ensaio.É isso que permite consultar com sessions e stats`--rm`. 

Para apagar o histórico de capturas:

```bash
rm -f data/traffic.db
```

Se aparecer `Permission denied`, use `sudo rm -f data/traffic.db`. Quando a pasta `data/` é criada pelo Docker, ela pertence ao root. O banco é recriado automaticamente na próxima execução.

---

<br>

## Troubleshooting

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `wsl --install` falha com erro de virtualização | Virtualização desativada | Ative Intel VT-x/AMD-V na BIOS/UEFI |
| `permission denied while trying to connect to the Docker daemon socket` | Usuário fora do grupo `docker` | Etapa 1.5 (`usermod` + `wsl --shutdown`) |
| `Cannot connect to the Docker daemon` | Serviço do Docker parado | `sudo systemctl start docker`. Se o `systemctl` não funcionar no WSL, habilite o systemd: adicione `[boot]` e `systemd=true` em `/etc/wsl.conf` e execute `wsl --shutdown` |
| `Interface '...' not found` | O nome da interface é outro nesta máquina | Use um nome listado na própria mensagem ou em `ip -br link` |
| `ERROR: [Errno 1] Operation not permitted` na captura ao vivo | O processo não tem a capability `NET_RAW` (ex.: `cap_drop`, Docker rootless ou execução fora do container sem root) | Execute pelo `docker compose` do projeto, que roda como root com `NET_RAW` |
| A captura ao vivo termina com 0 pacotes | Não havia tráfego, ou o filtro excluiu tudo | Gere tráfego (`ping`) durante a captura; revise o `--filter` |
| `--count` não termina | A quantidade ainda não foi atingida | Use `--duration` ou Ctrl+C |
| `pcap file not found` | Comando fora da raiz do repositório | `cd ~/Analizador-de-trafego` |
| `stats` com números maiores que a referência | Sem `--session`, as sessões são somadas | Use `stats --session N` ou limpe o banco (Etapa 10) |
| `Not a supported capture file` | O arquivo não é uma captura válida (pcap ou pcapng) | Confira o arquivo; reexporte pelo Wireshark |

---

