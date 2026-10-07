PY ?= python
impl ?= conformance.toy

.PHONY: test conformance mutants lint
test: lint
	$(PY) -m pytest

conformance:
	$(PY) -m pytest conformance/stages --impl $(impl)

mutants:
	$(PY) -m pytest conformance/test_mutants.py

lint:
	$(PY) -m ruff check --select E9,F pipeline conformance tests scripts experiments

# make new-strategy name=my_momentum  (also new-data, new-feature, new-pricing, new-risk, new-portfolio,
# new-execution, new-validation)
new-%:
	$(PY) scripts/new_stage.py $* $(name)
