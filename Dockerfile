# Imagem construída em estágios (multi-stage): uma base comum e dois destinos,
# "test" (testes e verificações) e "runtime" (execução da aplicação).

FROM python:3.13-slim AS base

# Não gera arquivos .pyc e exibe os logs imediatamente, sem buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# O tcpdump traz a biblioteca libpcap, usada pelo Scapy para aplicar os
# filtros de captura (--filter). A limpeza do cache do apt reduz a imagem.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tcpdump \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# As dependências são instaladas antes de copiar o código para aproveitar o
# cache do Docker: alterar o código não reinstala as bibliotecas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Estágio de testes: base + ferramentas de qualidade, testes, amostra e script
# do portão de qualidade. Nada disso vai para a imagem de execução.
FROM base AS test
COPY requirements-dev.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests/ ./tests/
COPY samples/ ./samples/
COPY scripts/ ./scripts/
ENTRYPOINT ["python", "-m", "pytest", "-v"]

# Estágio de execução (padrão). pip só é usado no build e é removido da
# imagem final (ver docs/seguranca.md).
FROM base AS runtime
RUN pip uninstall -y pip
ENTRYPOINT ["python", "-m", "app"]
