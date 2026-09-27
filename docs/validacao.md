# Guia de execução e validação

Passo a passo para preparar o ambiente, executar a aplicação e conferir o resultado de cada comando. Siga as etapas na ordem. Cada uma traz o objetivo, os comandos e o **resultado esperado**. 

A captura ao vivo varia com o ambiente: ela serve para comprovar o funcionamento da captura.

<br>

## Por onde começar

| Seu ambiente | Comece em |
|---|---|
| **Windows 10/11** | [Etapa 1 — Verificar e preparar o Windows](#etapa-1--verificar-e-preparar-o-windows) |
| **Linux ou Windows com Docker Engine e Docker Compose** | [Etapa 2 — Verificar os pré-requisitos](#etapa-2--verificar-os-pré-requisitos) |

> **Ambiente de homologação:** este guia foi validado em máquinas com Windows 10 e Windows 11, considerando cenários com e sem distribuição Linux previamente instalada, ambos com e sem Docker previamente configurados. Nesses cenários foi valido. Embora para validação completa, recomendo seguir o guia com uma nova instalação. 

> **Por escolhi WSL2 com Docker Engine, e não Docker Desktop?**
> 
> A captura ao vivo precisa enxergar uma interface de rede do ambiente Linux onde o tráfego de teste é gerado. Com o Docker Engine executado dentro do WSL2, o container utiliza a rede desse Linux e consegue capturar na interface `eth0` do WSL. Isso mantém identificação da interface, geração de tráfego, Docker e captura no mesmo contexto de rede. A decisão e o custo aceito estão detalhados em [docs/decisoes.md](decisoes.md).

---

<br>

## Etapa 1 — Verificar e preparar o Windows

**Objetivo:** identificar o que já está disponível na máquina e instalar somente os componentes necessários para executar e validar a aplicação.

> Se a máquina já possuir Ubuntu no WSL2, Git ou Docker Engine, não é necessário recriar o ambiente. As próximas etapas verificam o estado atual da máquina e permitem avançar sempre que os pré-requisitos já estiverem atendidos. Embora para validação ideal continuo recomendando uma nova instalação. A preparação do WSL2 e do Docker Engine é necessária apenas uma vez.

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

Se `Ubuntu-24.04` já aparecer com `VERSION` igual a `2`, e o `STATE` como `RUNNING` o ambiente Linux necessário já está disponível. avance para a [Etapa 1.4](#14-verificar-git-e-docker-engine).

Se o Ubuntu 24.04 não estiver listado ou o WSL ainda não estiver disponível, continue para a próxima etapa. 

> O objetivo desta verificação é evitar alterações desnecessárias em um ambiente de uso de laboratório que já possua parte do ambiente preparado.
> Caso tenha o ambiente linux, faça sua avaliação de utilização para esse Guia.

<br>

### 1.2 Instalar e provisionar o Ubuntu 24.04, se necessário

Esta etapa só é necessária se o Ubuntu 24.04 não tiver sido identificado na verificação anterior.

No **PowerShell como administrador**, execute:

```powershell
wsl --install -d Ubuntu-24.04
```

> O comando baixa, instala e registra o Ubuntu 24.04 no WSL2. Ao concluir a instalação, o próprio processo inicia o primeiro provisionamento da distribuição. Pode ser necessário reiniciar o computador para aplicar as alterações.

Uma sequência semelhante à abaixo será exibida:

```text
Baixando: linux 24.04 LTS
Instalando: linux 24.04 LTS
Distribuição instalada com êxito.
Iniciando Ubuntu-24.04...
Provisioning the new WSL instance Ubuntu-24.04
This might take a while...
```
Se o computador pedir para reiniciar, reinicie.

> **Observação:** antes de avançar, confirme que o Ubuntu-24.04 está instalado como WSL2 e consegue ser iniciado. Se estiver Stopped, execute 'wsl -d Ubuntu-24.04', se o provisionamento automatico iniciar, já crie um usuário e senha simples. Dando certo, desconsidere os próximos itens avançando paras as etapas.

<br>

Quando aparecer:

```text
Create a default Unix user account:
```

crie o usuário Linux. Para manter os exemplos deste guia padronizados, pode ser utilizado:

```text
desafio
```

Em seguida, defina uma senha local simples:

```text
New password: desafio
Retype new password: desafio
```
> A senha não aparece na tela enquanto é digitada. Esse comportamento é normal no Linux.

Após a confirmação, deve aparecer:

```text
passwd: password updated successfully
To run a command as administrator (user "root"), use "sudo <command>".
```

Ao final do provisionamento, o ambiente Ubuntu estará pronto para continuar o guia.

> Nesse momento feche o PowerSheel e na barra de pesquisa procure pelo aplicativo `Ubuntu` deve aparece **Ubuntu-24.04**. Execute-o para continuar o provisionamento. 

**> A partir deste ponto, os comandos do projeto são executados no ambiente Ubuntu**, exceto quando o guia indicar explicitamente o PowerShell.

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
| `git --version` | 2.43.0 |
| `docker --version` | Exibe a versão instalada do Docker |
| `docker compose version` | Exibe a versão do Docker Compose |

Se os quatro comandos responderem corretamente, não é necessário reinstalar Git ou Docker Engine. Avance para a [Etapa 2](#etapa-2--verificar-os-pré-requisitos).

**Só se algum componente não estiver disponível, continue para a próxima etapa.**

<br>

### 1.5 Instalar Git e Docker Engine no Ubuntu, se necessário

Os comandos abaixo utilizam `sudo` porque algumas etapas exigem privilégio administrativo dentro do Ubuntu. Na primeira execução de um comando com `sudo`, o terminal solicitará a senha do usuário Linux criado durante o provisionamento, que é: `desafio`

Digite a senha definida anteriormente e pressione Enter. A senha não é exibida na tela enquanto é digitada. Esse comportamento é normal no Linux. Depois da autenticação, o sudo pode manter a autorização por alguns minutos, então a senha normalmente não é solicitada novamente em cada comando.

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

Por padrão, o Docker pode exigir privilégios administrativos para ser utilizado. Adicione o usuário atual do Ubuntu ao grupo `docker`:

No **terminal do Ubuntu**, execute:

```bash
sudo usermod -aG docker $USER
```

> O comando normalmente não exibe nenhuma mensagem quando é concluído com sucesso. A nova associação ao grupo só será aplicada em uma nova sessão do usuário. 

Para reiniciar o ambiente WSL, primeiro saia do terminal Ubuntu:

```bash
exit
```

Agora, no **PowerShell do Windows**, execute:

```powershell
wsl --shutdown
```
<br>

> `wsl --shutdown` é um comando do Windows e deve ser executado no PowerShell ou Prompt de Comando, não dentro do Ubuntu.

Depois, inicie novamente o Ubuntu. Abrar `Ubuntu-24.04` pelo menu Iniciar do windows. 

> Na próxima inicialização do Terminal do Ubuntu, aguarde um pouco. O Terminal recarregá.

No **terminal do Ubuntu**, confira:

```bash
groups
systemctl is-active docker
```

**Resultado esperado:**

- `docker` aparece na lista de grupos do usuário;
- o serviço Docker responde `active`.

Por exemplo:

```text
desafio adm cdrom sudo dip plugdev users docker
active
```

A preparação do inicial do Windows está concluída.

---

<br>

## Etapa 2 — Verificar os pré-requisitos

**Objetivo:** confirmar que Git, Docker Engine e Docker Compose estão funcionando antes de importar ou executar o projeto.

Esta etapa é o ponto comum para:

- Windows e Linux preparado pelas etapas.

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
| `docker compose version` | `Docker Compose version v5.x.x` |
| `Hello from Docker!` |

O ambiente está pronto para importar o projeto.

---

<br>

## Etapa 3 — Importar o projeto

**Objetivo:** Vamos importar uma cópia local do projeto no github e validar que os arquivos necessários estão disponíveis.

Continue no **mesmo terminal do Ubuntu** utilizado na etapa anterior.

<br>

### 3.1 Confirmar o diretório de trabalho

Vá para a pasta pessoal do usuário Linux:

```bash
cd
pwd
```

**Resultado esperado:** um caminho semelhante a:

```text
/home/usuario
```

> No WSL2, mantenha o projeto dentro do sistema de arquivos Linux, e não em diretórios montados do Windows como `/mnt/c/...`. Isso mantém Git, Docker e os comandos de validação no mesmo ambiente Linux utilizado pelo projeto.

<br>

### 3.2 Clonar o repositório

Execute agora:

```bash
git clone https://github.com/brunodrapalski-hue/Analizador-de-trafego.git
```

Como o repositório é público, não é necessária autenticação para essa operação.

**Resultado esperado:** o Git cria a pasta `Analizador-de-trafego` e finaliza com mensagens semelhantes a:

```text
Cloning into 'Analizador-de-trafego'...
Receiving objects: 100% (...)
Resolving deltas: 100% (...)
```

> O clone precisa ser realizado apenas uma vez. Se a pasta `Analizador-de-trafego` já existir porque o projeto foi clonado anteriormente. Prossiga para a próxima etapa.

<br>

### 3.3 Entrar no diretório do projeto

Execute:

```bash
cd Analizador-de-trafego
pwd
```

**Resultado esperado:** o caminho termina em:

```text
/Analizador-de-trafego
```

<br>

### 3.4 Conferir os arquivos

Execute:

```bash
ls
```

**Resultado esperado:** serão listados, entre outros:

```text
Dockerfile
README.md
app
docker-compose.yml
docs
pyproject.toml
requirements-dev.txt
requirements.txt
samples
scripts
tests
```

> **A partir deste ponto, todos os comandos do projeto devem ser executados dentro de `~/Analizador-de-trafego`**, salvo quando o guia indicar explicitamente outro diretório.

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

- O build termina sem erro. Na primeira vez leva uns segundos a mais, porque baixa a imagem base.
- Sera mostrad `traffic-analyzer` com a tag `1.0.0`.
- O `--help` mostra `usage: traffic-analyzer [-h] [--db DB] {capture,stats,sessions} ...`.

---

<br>

# Etapa 5 — Validar o processamento com o PCAP de referência

**Objetivo:** validar, com uma entrada conhecida e reproduzível, o fluxo de processamento da aplicação: leitura dos pacotes → interpretação dos metadados → persistência no SQLite → cálculo e apresentação das estatísticas.

O arquivo `samples/demo.pcap` foi incluído como amostra de referência para esta validação. Como seu conteúdo deixei estático, os resultados obtidos podem ser comparados com valores conhecidos, sem depender do tráfego disponível na rede naquele momento.

> Esta etapa não substitui a captura ao vivo. O `.pcap` é utilizado para validar de o processamento, o armazenamento e as estatísticas. A captura real de uma interface será validada nas próximas etapas.


Continue no diretório do terminal ubuntu dentro do: ~/Analizador-de-trafego


Execute:

```bash
docker compose run --rm analyzer capture --pcap samples/demo.pcap
```

> O comando lê os pacotes da amostra pelo mesmo `PacketCollector` utilizado pela captura ao vivo, grava os metadados no banco e, ao final da sessão, calcula e exibe as estatísticas correspondentes.


**Resultado esperado:** são exibidos o resumo da sessão, a distribuição por protocolo e os rankings de IPs de origem e destino. A saída completa utilizada como referência está disponível em [docs/evidencias/01-estatisticas-demo-pcap.txt](evidencias/01-estatisticas-demo-pcap.txt).


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

---

<br>

## Etapa 6 — Validar a captura ao vivo

Com o ambiente já validado, vamos agora ao requisito principal do desafio: capturar pacotes em tempo real a partir de uma interface de rede especificada.

Na etapa anterior, o arquivo `samples/demo.pcap` foi utilizado como uma entrada conhecida para validar o processamento, a persistência e a geração das estatísticas de forma reproduzível. Agora, a origem dos pacotes será uma **interface de rede real do ambiente**. A aplicação utilizará o Scapy para escutar essa interface, processar os pacotes recebidos, armazenar seus metadados no SQLite e apresentar as estatísticas ao final da captura.

O tráfego será gerado dentro do próprio Ubuntu. Como o container ele consegue observar as interfaces de rede desse ambiente Linux e realizar a captura diretamente na interface selecionada.

<br>

### 6.1 Identificar a interface de rede

Continue no **terminal do Ubuntu** dentro (cd ~/Analizador-de-trafego) e e execute:

```bash
ip -br link
```
**Resultado esperado:** a lista de interfaces de rede disponíveis na sua máquina. O nome da interface principal varia conforme o ambiente e a aplicação escolherá.

```text
lo               UNKNOWN        00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>
eth0             UP             00:15:5d:xx:xx:xx <BROADCAST,MULTICAST,UP,LOWER_UP>
docker0          DOWN           02:42:xx:xx:xx:xx <NO-CARRIER,BROADCAST,MULTICAST,UP>
```

<br>

### 6.2 Capturar por 30 segundos gerando tráfego

Nesta etapa, escohi que a captura ao vivo será validada em dois cenários.

A primeira execução utiliza tráfego simples e tem como objetivo confirmar rapidamente que a aplicação consegue capturar pacotes da interface, armazenar os metadados e gerar as estatísticas ao final da sessão. Na segunda execução, pensei em utilizar um gerador de tráfego controlado para disparar diferentes protocolos durante a captura. Isso permite observar como a distribuição apresentada pela aplicação muda quando a entrada se torna mais variada.

As duas capturas utilizam uma janela de **30 segundos** apenas para manter a validação curta e previsível. A duração pode ser alterada por `--duration`, a captura pode ser encerrada por quantidade de frames com `--count` ou manualmente com `Ctrl+C`.

**Nesse momento, abra um segundo terminal Ubuntu, deixe-os abertos já no diretório correto:**

```bash
cd ~/Analizador-de-trafego
```

<br>

#### 6.2.1 Validação básica da captura

O primeiro teste utiliza apenas alguns comandos de rede comuns. A intenção é validar a estrutura da captura ao vivo antes de gerar um conjunto maior e mais controlado de pacotes.


No **Terminal 1**, inicie uma captura de 30 segundos:

```bash
docker compose run --rm analyzer capture --iface auto --duration 30
```

**Resultado esperado:** a aplicação identifica automaticamente a interface utilizada pela rota padrão e inicia a captura:

```text
INFO: Interface detected automatically: eth0
INFO: Capturing on eth0 (press Ctrl+C to stop)...
```

> O nome da interface varia conforme a máquina e a configuração de rede.


Enquanto a captura estiver ativa, execute no **Terminal 2**:

```bash
ping -c 10 1.1.1.1
curl -s -o /dev/null https://github.com && echo OK
```

O `ping` produz tráfego ICMP, enquanto a requisição ao GitHub produz tráfego associado a uma conexão TCP/HTTPS.

Esse primeiro cenário é propositalmente simples. O objetivo não é preencher todas as categorias do relatório, mas confirmar que:

- a interface foi detectada;
- os pacotes estão sendo recebidos;
- os metadados estão sendo gravados;
- a sessão termina corretamente;
- as estatísticas são calculadas e exibidas.


Após 30 segundos, o **Terminal 1** encerra a captura automaticamente e apresenta uma mensagem semelhante a:

```text
INFO: Session N finished: ... packets stored, ... non-IP packets ignored.
```


Em seguida, são exibidas as estatísticas da sessão.

Além do tráfego gerado manualmente, outros protocolos podem aparecer porque a interface continua recebendo o tráfego normal do sistema.

<br>

#### 6.2.2 Validação ampliada com tráfego controlado

Depois de confirmar o funcionamento básico, execute uma segunda captura.

Nesta validação, a intenção é gerar diferentes categorias de tráfego para observar como elas são classificadas pela aplicação e como o resultado se diferencia da primeira execução.


No **Terminal 1**, inicie novamente uma captura de 30 segundos:

```bash
docker compose run --rm analyzer capture --iface auto --duration 30
```


Assim que a captura começar, **copie o bloco abaixo inteiro** e execute no **Terminal 2**.

O script utiliza o Scapy e as bibliotecas Python já presentes. Durante aproximadamente **25 segundos**, ele gera o tráfego representando as categorias tratadas pela aplicação.


O gerador utiliza 25 segundos, e não 30, para deixar uma pequena margem entre o início da captura no Terminal 1 e a execução do bloco no Terminal 2.

```bash
docker compose run --rm -T --entrypoint python analyzer - <<'EOF'
import logging
import socket
import time

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import (
    ARP,
    ICMP,
    IP,
    Ether,
    ICMPv6EchoRequest,
    IPv6,
    conf,
    send,
    sendp,
)

DESTINO = "1.1.1.1"
DURACAO = 25

iface, _, gateway = conf.route.route(DESTINO)

print(f"Gerando tráfego por {DURACAO} s na interface {iface}...")

fim = time.time() + DURACAO
rodadas = 0

while time.time() < fim:
    send(IP(dst=DESTINO) / ICMP(), verbose=0)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.sendto(b"teste", (DESTINO, 9999))

    try:
        socket.create_connection((DESTINO, 443), timeout=2).close()
    except OSError:
        pass

    sendp(
        Ether(dst="33:33:00:00:00:01")
        / IPv6(dst="ff02::1")
        / ICMPv6EchoRequest(),
        iface=iface,
        verbose=0,
    )

    send(IP(dst=DESTINO, proto=47) / b"teste", verbose=0)

    if gateway != "0.0.0.0":
        sendp(
            Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=gateway),
            iface=iface,
            verbose=0,
        )

    rodadas += 1
    time.sleep(1)

print(
    f"Concluído: {rodadas} rodadas de "
    "ICMP, UDP, TCP, ICMPv6, OTHER (GRE) e ARP."
)
EOF
```


O tráfego gerado foi escolhido para exercitar as diferentes categorias reconhecidas pela aplicação:


| Tipo | Tráfego gerado | Onde aparece |
|---|---|---|
| ICMP | pacote IPv4 ICMP para `1.1.1.1` | `ICMP` |
| UDP | datagrama UDP para `1.1.1.1:9999` | `UDP` |
| TCP | tentativa de conexão com `1.1.1.1:443` | `TCP` |
| ICMPv6 | ICMPv6 para `ff02::1` | `ICMPv6` |
| OTHER | pacote IP com protocolo 47 (GRE) | `OTHER` |
| ARP | consulta ARP ao gateway | `Non-IP packets ignored` |


**Resultado esperado no Terminal 2:** uma saída semelhante a:

```text
Gerando tráfego por 25 s na interface eth0...
Concluído: 23 rodadas de ICMP, UDP, TCP, ICMPv6, OTHER (GRE) e ARP.
```


O nome da interface e a quantidade de rodadas podem variar. Após os 30 segundos, o **Terminal 1** encerra a captura e apresenta novamente as estatísticas da sessão.

Nesta segunda execução, a tabela `Packets by protocol` deve permitir observar uma variedade maior de categorias, incluindo **TCP, UDP, ICMP, ICMPv6 e OTHER**. Os pacotes ARP são contabilizados no resumo como `Non-IP packets ignored`.

<br>

#### Comparar as duas validações

As duas execuções criam sessões independentes no banco de dados.

A primeira demonstra o comportamento da aplicação com uma pequena quantidade de tráfego gerado manualmente. A segunda utiliza uma entrada mais controlada e diversificada para exercitar as categorias de protocolo tratadas pelo parser.


Para visualizar as sessões criadas:

```bash
docker compose run --rm analyzer sessions
```


Os resultados podem ser consultados individualmente utilizando o ID de cada sessão:

```bash
docker compose run --rm analyzer stats --session N
```


Ao comparar as duas execuções, espera-se que a segunda apresente uma distribuição de protocolos mais diversificada. Os valores absolutos não precisam ser iguais entre máquinas ou execuções, pois o tráfego normal do ambiente continua sendo capturado junto com o tráfego gerado pelo teste.

Essa comparação permite validar não apenas que a aplicação está recebendo pacotes reais, mas também que diferentes tipos de tráfego são interpretados, persistidos e refletidos corretamente nas estatísticas.

<br>

### 6.3 Outras formas de encerrar e filtrar (Agora é opcional para explorar!)

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
