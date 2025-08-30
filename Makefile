.PHONY: venv fmt lint test run-dry run-paper digest

venv:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

fmt:
	@echo "Using ruff-format via ruff not included; relying on black equivalent not pinned here."

lint:
	@echo "Lint step placeholder (ruff/flake8 can be added later)."

test:
	. .venv/bin/activate && pytest -q

run-dry:
	. .venv/bin/activate && EXECUTOR_MODE=DRY_RUN DASH_TOKEN=$${DASH_TOKEN:-change-me} .venv/bin/uvicorn ops.dashboard.app:app --host 0.0.0.0 --port 9090

run-paper:
	. .venv/bin/activate && EXECUTOR_MODE=PAPER DASH_TOKEN=$${DASH_TOKEN:-change-me} .venv/bin/uvicorn ops.dashboard.app:app --host 0.0.0.0 --port 9090

digest:
	. .venv/bin/activate && python scripts/digest.py
