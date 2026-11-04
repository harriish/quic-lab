FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY docker/entrypoint.sh /usr/local/bin/quic-entrypoint
RUN chmod +x /usr/local/bin/quic-entrypoint

# Self-signed cert is generated on first start (see entrypoint).
ENTRYPOINT ["quic-entrypoint"]
CMD ["python", "-m", "quic_lab", "server", "--host", "0.0.0.0", "--port", "4433"]
