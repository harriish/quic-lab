.PYTHON ?= python3

.PHONY: certs server client test lint docker-up docker-down tf-init tf-plan tf-apply tf-destroy

certs:
	bash scripts/gen_certs.sh certs

server:
	$(PYTHON) -m quic_lab server

client:
	$(PYTHON) -m quic_lab client --runs 2

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src tests

docker-up:
	docker compose up --build -d server

docker-down:
	docker compose down -v

tf-init:
	terraform -chdir=infra init

tf-plan:
	terraform -chdir=infra plan

tf-apply:
	terraform -chdir=infra apply

tf-destroy:
	terraform -chdir=infra destroy
