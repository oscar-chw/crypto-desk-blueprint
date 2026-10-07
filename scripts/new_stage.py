#!/usr/bin/env python3
"""Scaffold a stub implementation of one stage, wired to that stage's conformance suite.

    python scripts/new_stage.py <stage> <name>        (or: make new-<stage> name=<name>)

Creates implementations/<name>/__init__.py. Every other stage is re-exported from conformance/toy, so the
new package is a complete implementation from the first minute; the stub stage raises NotImplementedError
and its suite fails until you implement it. Never edit the suite to make the stub pass.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STAGES = {
    "data": ("make_data_source", "test_data.py", "DataSource",
             "    def bars(self, instrument_id, start, end):\n"),
    "feature": ("make_feature", "test_features.py", "Feature",
                '    name = "{name}"\n    lookback = 2\n\n    def compute(self, bars):\n'),
    "strategy": ("make_strategy", "test_strategy.py", "Strategy",
                 '    model_id = "{name}"\n\n    def signal(self, instrument_id, t, features):\n'),
    "pricing": ("make_pricing", "test_pricing.py", "PricingModel",
                "    def fair_value(self, instrument_id, t, spot, expiry, r_quote, r_base):\n"
                "        raise NotImplementedError\n\n"
                "    def funding_cashflow(self, position_qty, mark_price, rate):\n"),
    "risk": ("make_risk_model", "test_risk.py", "RiskModel",
             "    def forecast(self, t, returns):\n"),
    "portfolio": ("make_portfolio", "test_portfolio.py", "PortfolioConstructor",
                  "    max_gross = 1.0\n\n    def target(self, t, signals, risk):\n"),
    "execution": ("make_executor", "test_execution.py", "Executor",
                  "    def orders(self, target, account):\n"),
    "validation": ("make_cv_splitter", "test_validation.py", "Splitter",
                   "    embargo_ns = 0\n\n    def split(self, t0, t1):\n"),
}

TEMPLATE = '''"""{name}: a {stage} implementation (contract: pipeline.protocols.{proto}).

Every other stage comes from the toy until you replace it. Run its suite with:
    pytest conformance/stages/{test} --impl implementations.{name}
"""
from conformance.toy import *  # noqa: F401,F403


class {cls}:
{body}        raise NotImplementedError("implement me, then run the conformance suite")


def {factory}():
    return {cls}()
'''


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in STAGES:
        print(__doc__.strip() + "\n\nstages: " + ", ".join(STAGES))
        return 2
    stage, name = argv
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        print(f"name must be a lowercase Python identifier, got {name!r}")
        return 2
    factory, test, proto, body = STAGES[stage]
    pkg = ROOT / "implementations" / name
    if pkg.exists():
        print(f"refusing to overwrite {pkg}")
        return 1
    pkg.mkdir(parents=True)
    (ROOT / "implementations" / "__init__.py").touch()
    cls = "".join(p.capitalize() for p in name.split("_"))
    (pkg / "__init__.py").write_text(TEMPLATE.format(name=name, stage=stage, proto=proto, test=test, cls=cls,
                                                     body=body.format(name=name), factory=factory))
    print(f"created {pkg.relative_to(ROOT)}/__init__.py\n"
          f"next: pytest conformance/stages/{test} --impl implementations.{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
