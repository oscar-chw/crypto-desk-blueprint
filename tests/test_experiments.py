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


MODULES = {}


def _load(path: Path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_experiments
    if path not in MODULES:
        MODULES[path] = run_experiments.load(path)
    return MODULES[path]


def _mod(exp_id: str):
    return _load(next(p for p in SCRIPTS if p.name.startswith(exp_id + "-")))


def test_every_blueprint_experiment_has_a_script():
    assert len(MENTIONED) == 20, MENTIONED  # an empty or truncated scan must fail, not pass
    have = {p.name[:8] for p in SCRIPTS}
    assert set(MENTIONED) == have, set(MENTIONED) ^ have


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name[:8])
def test_quick_run_writes_valid_result(path, tmp_path):
    mod = _load(path)
    execute(mod.META, mod.run, quick=True, out_dir=tmp_path)
    on_disk = json.loads((tmp_path / f"{mod.META['id']}.json").read_text())
    assert on_disk["id"] == path.name[:8] and on_disk["quick"] is True
    validate(on_disk)  # schema, both arms with finite numbers, an uncertainty, a valid verdict
    assert on_disk["treatment"]["arm"] != on_disk["control"]["arm"]


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


# Hand-made inputs on both sides of each verdict rule: an inverted inequality, a dropped leg or a wrong
# threshold in any passes() flips one of these.
T_, F_ = True, False
VERDICT_CASES = [
    ("EXP-00-1", [(0, 5)], [(1, 5), (0, 0)]),
    ("EXP-00-2", [(0.01, 0.001, [0.1, 0.2, 0.3])], [(0.001, 0.001, [0.1, 0.2, 0.3]), (0.01, 0.001, [0.1, 0.3, 0.2])]),
    ("EXP-01-1", [(0.5, 0.1)], [(0.1, 0.1), (-0.5, 0.1)]),
    ("EXP-01-2", [(-0.5, 0.1, -0.5, 0.1)], [(-0.5, 0.1, -0.1, 0.1), (-0.1, 0.1, -0.5, 0.1)]),
    ("EXP-02-1", [(0.2, 0.01, 0.001, 0.002)], [(0.2, 0.01, -0.009, 0.002), (0.01, 0.01, 0.0, 0.002)]),
    ("EXP-02-2", [(0.8, 0.01, 0.05, 1000)], [(0.06, 0.01, 0.05, 1000), (0.8, 0.01, 0.2, 1000)]),
    ("EXP-02-3", [([0.1, 0.9],)], [([0.85, 0.95],)]),
    ("EXP-03-1", [(-0.4, 0.01, 0.0, 0.001)], [(-0.4, 0.01, 0.018, 0.0016), (0.0, 0.01, 0.0, 0.001)]),
    ("EXP-03-2", [([(0.01, 0.02)], 0.05, 1000)], [([(0.5, 0.05)], 0.05, 1000), ([(0.0, 0.1)], 0.10, 1000)]),
    ("EXP-04-1", [([0.34, 0.35], [0.17, 0.14])], [([0.34, 0.10], [0.17, 0.14])]),
    ("EXP-04-2", [([0.05, 1.0],)], [([0.05, 0.09],)]),
    ("EXP-05-1", [(-0.08, 0.001, 0.29, 0.43)], [(-0.08, 0.001, 0.5, 0.43), (0.0, 0.001, 0.29, 0.43)]),
    ("EXP-05-2", [(-0.4, 0.02)], [(-0.01, 0.02), (0.4, 0.02)]),
    ("EXP-05-3", [(0.12, 0.006)], [(0.005, 0.006), (-0.12, 0.006)]),
    ("EXP-06-1", [([(-0.2, 0.01), (-0.1, 0.01)],)], [([(-0.2, 0.01), (0.0, 0.01)],)]),
    ("EXP-06-2", [(-0.3, 0.02)], [(0.0, 0.02), (0.3, 0.02)]),
    ("EXP-07-1", [([T_, T_, T_], 0.016, 0.005, 1)],
     [([T_, T_, T_], 0.002, 0.005, 1), ([T_, F_, T_], 0.016, 0.005, 1), ([T_, T_, T_], 0.016, 0.005, None)]),
    ("EXP-07-2", [([(1.3, 0.04)],)], [([(0.01, 0.04)],), ([(-1.3, 0.04)],)]),
    ("EXP-08-1", [(0.66, 0.005, 0.495, 0.008)], [(0.51, 0.008, 0.495, 0.008), (0.66, 0.005, 0.45, 0.008)]),
    ("EXP-08-2", [([0.05, 0.4, 0.99, 1.0], [0.007, 0.015, 0.003, 0.001], [0.05, 0.0, 0.0, 0.003], 1000)],
     [([0.05, 0.4, 0.3, 1.0], [0.007, 0.015, 0.003, 0.001], [0.05, 0.0, 0.0, 0.003], 1000),
      ([0.05, 0.4, 0.99, 1.0], [0.007, 0.015, 0.003, 0.001], [0.05, 0.2, 0.0, 0.003], 1000)]),
]


def test_every_experiment_has_verdict_cases():
    assert sorted(c[0] for c in VERDICT_CASES) == MENTIONED


@pytest.mark.parametrize("exp_id,good,bad", VERDICT_CASES, ids=[c[0] for c in VERDICT_CASES])
def test_verdict_function_flips(exp_id, good, bad):
    passes = _mod(exp_id).passes
    for args in good:
        assert bool(passes(*args)), args
    for args in bad:
        assert not passes(*args), args


# The docs are generated from results/*.json; a hand edit or a stale table must fail here.
RESULTS = {json.loads(p.read_text())["id"]: json.loads(p.read_text()) for p in (ROOT / "results").glob("EXP-*.json")}


def test_docs_match_results():
    assert sorted(RESULTS) == MENTIONED
    ev = (ROOT / "blueprint" / "EVIDENCE.md").read_text()
    readme = (ROOT / "README.md").read_text()
    bad = sorted(k for k, r in RESULTS.items() if r["verdict"] != "supports")
    counts = f"{20 - len(bad)} of 20 experiments support their rule." + (f" Not supported: {', '.join(bad)}." if bad else "")
    assert counts in ev and counts in readme
    rows = [line for line in ev.splitlines() if line.startswith("| [EXP-")]
    assert len(rows) == 20
    for k, r in RESULTS.items():
        assert not r["quick"], k
        v = r["verdict"] if r["verdict"] == "supports" else f"**{r['verdict']}**"
        assert f"{r['summary']} ([json](../results/{k}.json)) | {v} |" in ev, k
        stage = next((ROOT / "blueprint").glob(r["backs"].split(" ")[0] + ".md")).read_text()
        assert f"`result: {r['verdict']}: {r['summary']}`" in stage, k
        assert f"[{k}](EVIDENCE.md): {r['verdict']}; {r['summary']} |" in (ROOT / "blueprint" / "FOUNDATIONS.md").read_text() \
            or k not in (ROOT / "blueprint" / "FOUNDATIONS.md").read_text(), k
