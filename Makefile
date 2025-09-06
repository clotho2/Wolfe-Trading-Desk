# path: Makefile
.PHONY: fmt lint test cov ci spec-diff

PY ?= python

fmt:
	ruff --fix .
	black .

lint:
	ruff .
	black --check .

test:
	pytest -q

cov:
	pytest --cov --cov-report=term-missing

ci:
	ruff .
	black --check .
	pytest --cov --cov-report=xml --cov-report=term-missing
	$(PY) .ci/coverage_gate.py

# Allow override of spec paths:
SPEC_FROM ?= specs/v0_4_2.md
SPEC_TO   ?= specs/v0_4_3_delta.md
spec-diff:
	$(PY) tools/spec_diff.py --from $(SPEC_FROM) --to $(SPEC_TO)

