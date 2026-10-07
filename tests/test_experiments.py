"""Every evidence experiment runs in quick mode (small n, same code path) and writes a valid result with
both arms computed. Named failure: an experiment that crashes, drops its control arm or reports an effect
with no uncertainty would otherwise only show up in a multi-minute full run nobody repeats."""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from experiments._common import ROOT, execute, validate

pytestmark = pytest.mark.experiments
SCRIPTS = sorted((ROOT / "experiments").glob("EXP-*.py"))
MENTIONED = sorted({m for f in (ROOT / "blueprint").glob("0*.md") for m in re.findall(r"EXP-\d\d-\d", f.read_text())})


def _load(path: Path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_experiments
    return run_experiments.load(path)


def test_every_blueprint_experiment_has_a_script():
    assert len(MENTIONED) == 20, MENTIONED  # an empty or truncated scan must fail, not pass
    have = {p.name[:8] for p in SCRIPTS}
    assert set(MENTIONED) == have, set(MENTIONED) ^ have


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name[:8])
def test_quick_run_writes_valid_result(path, tmp_path):
    mod = _load(path)
    res = execute(mod.META, mod.run, quick=True, out_dir=tmp_path)
    on_disk = json.loads((tmp_path / f"{mod.META['id']}.json").read_text())
    assert on_disk["id"] == path.name[:8] and on_disk["quick"] is True
    validate(on_disk)  # schema, both arms with finite numbers, an uncertainty, a valid verdict
    assert on_disk["treatment"]["arm"] != on_disk["control"]["arm"]
    assert res["verdict_rule"] and res["seeds"] == on_disk["seeds"]


GOOD = {"id": "EXP-99-9", "backs": "x", "claim": "x", "script": "x", "data": {"kind": "synthetic"},
        "inputs": {}, "seeds": [1], "quick": True, "metric": "m", "treatment": {"arm": "t", "v": 1.0},
        "control": {"arm": "c", "v": 0.5}, "effect": {"estimate": 0.5, "se": 0.1}, "verdict": "supports",
        "verdict_rule": "r", "summary": "s", "runtime_s": 0.1}


@pytest.mark.parametrize("breakage", ["no_control_numbers", "no_uncertainty", "bad_verdict", "missing_field",
                                      "synthetic_without_seed"])
def test_validate_rejects_broken_results(breakage):
    validate(GOOD)  # the control case passes
    bad = copy.deepcopy(GOOD)
    if breakage == "no_control_numbers":
        bad["control"] = {"arm": "c"}
    elif breakage == "no_uncertainty":
        bad["effect"] = {"estimate": 0.5}
    elif breakage == "bad_verdict":
        bad["verdict"] = "looks good"
    elif breakage == "missing_field":
        del bad["summary"]
    else:
        bad["seeds"] = []
    with pytest.raises(ValueError):
        validate(bad)


def test_runner_refuses_quick_without_out():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_experiments.py"), "--quick"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode != 0 and "--out" in r.stderr
