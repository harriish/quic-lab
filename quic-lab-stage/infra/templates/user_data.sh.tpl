#!/bin/bash
set -euxo pipefail

apt-get update
apt-get install -y docker.io docker-compose-v2
systemctl enable --now docker

mkdir -p /opt/quic-lab /data
cat > /opt/quic-lab/docker-compose.yml <<EOF
services:
  quic-server:
    container_name: quic-lab-server
    image: ${image}
    command: >-
      python -m quic_lab server
      --host 0.0.0.0 --port 443
      --metrics /data/metrics.jsonl
    ports:
      - "443:443/udp"
    volumes:
      - quic-data:/data
    restart: unless-stopped
volumes:
  quic-data: {}
EOF

cd /opt/quic-lab
docker compose up -d
