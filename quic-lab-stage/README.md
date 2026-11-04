# quic-lab

A minimal, hackable **QUIC (RFC 9000) implementation lab**: an echo server, an
instrumented client, JSONL connection metrics, Docker packaging and a
Terraform/AWS deployment — the full path from "protocol on localhost" to
"protocol running on an EC2 instance behind a security group".

Built with Python 3.11+ and [aioquic](https://aioquic.readthedocs.io/), the same
library powering real HTTP/3 stacks, over a custom ALPN (`quic-lab/1`).

```
                  ┌────────────────────────────────────┐
                  │        quic-lab server (aioquic)   │
 client ──QUIC──▶ │  QUIC packet → stream → frame echo │──▶ metrics.jsonl
 (client.py)      │  TLS 1.3 · UDP/4433 · streams      │    (per-connection
                  └────────────────────────────────────┘     JSON stats)
```

## What it demonstrates

- **QUIC transport basics**: UDP-based handshake with TLS 1.3 baked in, ALPN
  negotiation, and one bidirectional stream per request/response (no
  head-of-line blocking between streams).
- **Application framing over streams**: a 4-byte length-prefixed frame format
  (`src/quic_lab/protocol.py`) with incremental decoding and size limits.
- **TLS session resumption**: run the client with `--runs N`; the ticket from
  connection 1 is reused on later connections, visibly shortening the handshake.
- **Observability**: per-connection counters (frames, bytes, duration) appended
  to a JSONL file — parse with `jq` or ship to CloudWatch.
- **Ops stack**: Docker image + compose, GitHub Actions CI (lint + tests +
  image build), and Terraform for AWS (Ubuntu 24.04 EC2, security group with
  **UDP/443**, systemd Docker, default region `eu-north-1`/Stockholm).

## Quickstart (localhost)

```bash
pip install -e ".[dev]"      # or: pip install aioquic
make certs                   # self-signed cert (demo only)
make server                  # terminal 1: QUIC echo server on udp/4433
make client                  # terminal 2: echoes + handshake/RTT stats
make test                    # unit tests (framing + metrics)
```

Example client output:

```
run  1 | 127.0.0.1:4433 | handshake   42.7 ms | 5 msgs | rtt min/avg/max 1.8/2.3/3.1 ms | resumed ticket: no
run  2 | 127.0.0.1:4433 | handshake    9.4 ms | 5 msgs | rtt min/avg/max 1.7/2.0/2.6 ms | resumed ticket: yes
all echoes matched
```

Tail the metrics the server wrote:

```bash
jq . metrics.jsonl
```

## Docker

```bash
docker compose up --build -d server      # server on udp/4433
docker compose run --rm client           # demo client inside the network
```

The image generates a self-signed cert on first start (`docker/entrypoint.sh`).
Mount real certs via `QUIC_LAB_CERT_DIR` in production.

## AWS deployment (Terraform)

```bash
# 1. Build & push the image (ECR or GHCR), then point infra at it:
docker build -t <registry>/quic-lab:latest .
docker push <registry>/quic-lab:latest

# 2. Deploy:
cd infra
terraform init
terraform apply \
  -var="container_image=<registry>/quic-lab:latest" \
  -var="admin_cidr=$(curl -s https://checkip.amazonaws.com)/32"

terraform output quic_endpoint   # e.g. 1.2.3.4:443/udp
```

The EC2 user-data installs Docker and starts the server on **UDP/443** with
metrics persisted to a volume. Then:

```bash
python -m quic_lab client --host <PUBLIC_IP> --port 443 --runs 2
```

Notes:
- UDP/443 is open to `0.0.0.0/0` (QUIC clients can come from anywhere); SSH is
  restricted to `admin_cidr` — set it to your IP.
- Over the public internet the client's self-signed trust doesn't apply;
  pass `--ca` with the cert used on the server, or accept the default
  skip-verification for lab use only.
- Default region is `eu-north-1` (Stockholm).

## Repo layout

```
src/quic_lab/
  protocol.py     wire framing: 4-byte length prefix + decoder limits
  stats.py        per-connection counters → JSONL metrics
  server.py       aioquic echo server (ALPN quic-lab/1)
  client.py       instrumented client: handshake time, per-message RTT, resumption
  __main__.py     CLI: python -m quic_lab server|client
tests/            unit tests (framing, stats)
infra/            Terraform: VPC defaults, SG (UDP/443 + SSH), EC2 + user-data
docker/           container entrypoint (cert bootstrap)
scripts/          local cert generation
.github/          CI: ruff, pytest, docker build
```

## Extending it (ideas)

- 0-RTT: send early data during resumption instead of only resuming the ticket.
- HTTP/3: swap the echo protocol for aioquic's `H3Connection` and serve a JSON API.
- Datagrams: exercise unreliable QUIC datagrams (`version_negotiation`-style side channel).
- Prometheus exporter reading `metrics.jsonl`.
