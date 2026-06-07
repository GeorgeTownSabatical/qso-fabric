.PHONY: test bootstrap run run-local lint bench dev dev-bootstrap dev-lint dev-test dev-quick dev-smoke dev-all dev-ci dev-hook-install dev-submission solis-build solis-run solis-up solis-down solis-k8s-apply solis-k8s-dry solis-test solis-report

QSO_DEV ?= python3 tools/dev_automation.py

bootstrap:
	python3 -m venv .venv
	.venv/bin/python -m pip install -e '.[dev]'

test:
	.venv/bin/python -m pytest

run-local:
	.venv/bin/python main.py

run: solis-run

lint:
	.venv/bin/python -m ruff check .

bench:
	.venv/bin/python cmd/qso-node/benchmark_cli.py

# ------------------------------
# Development automation targets
# ------------------------------

dev: dev-quick

dev-bootstrap:
	$(QSO_DEV) bootstrap

dev-lint:
	$(QSO_DEV) lint

dev-test:
	$(QSO_DEV) test

dev-quick:
	$(QSO_DEV) quick

dev-smoke:
	$(QSO_DEV) smoke

dev-all:
	$(QSO_DEV) all

dev-ci:
	$(QSO_DEV) ci

dev-hook-install:
	$(QSO_DEV) hook-install

dev-submission:
	$(QSO_DEV) submission

# ------------------------------
# Solis (QSO-native) targets
# ------------------------------

SOLIS_IMAGE ?= solis-node:latest
SOLIS_DOCKERFILE ?= infra/docker/Dockerfile.solis
SOLIS_COMPOSE ?= infra/docker/docker-compose.solis.yml
K8S_DIR ?= infra/k8s
SOLIS_REPORT_VERSION ?=
SOLIS_REPORT_TIMESTAMP ?=
SOLIS_REPORT_VALIDATE_ONLY ?= 0

solis-build:
	docker build -f $(SOLIS_DOCKERFILE) -t $(SOLIS_IMAGE) .

solis-run: solis-build
	docker run --rm -p 9100:9100 $(SOLIS_IMAGE)

solis-up:
	docker compose -f $(SOLIS_COMPOSE) up --build

solis-down:
	docker compose -f $(SOLIS_COMPOSE) down

solis-test:
	pytest -q solis/tests

solis-k8s-apply:
	kubectl apply -f $(K8S_DIR)

solis-k8s-dry:
	kubectl apply -f $(K8S_DIR) --dry-run=client --validate=false

solis-report:
	python3 solis/reports/scripts/generate_report.py \
		--repo-root . \
		--version "$(SOLIS_REPORT_VERSION)" \
		--timestamp "$(SOLIS_REPORT_TIMESTAMP)" \
		--validate-only "$(SOLIS_REPORT_VALIDATE_ONLY)"
