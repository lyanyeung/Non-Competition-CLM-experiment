import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("nl", HERE / "16_plot_NL_Loo_three_phase.py")
nl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nl)


class NLTests(unittest.TestCase):
    def test_phase_dates_do_not_assume_400_400(self):
        self.assertEqual([(a, b, c, d) for a, b, c, d in nl.PHASES], [
            ("PRE50", "NORMAL", 1997, 2047), ("AD200", "AD", 2047, 2247),
            ("POST300", "NORMAL", 2247, 2547)])

    def test_missing_post_is_not_mistaken_for_complete(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            cases = Path(t) / "cases"; archive = Path(t) / "archive"
            for phase in ("PRE50", "AD200"): (cases / nl.CASES[phase]).mkdir(parents=True)
            def env(case, key):
                phase = case.name.rsplit("_", 1)[-1]
                return {("PRE50", "RUN_STARTDATE"): "1997-01-01",
                        ("AD200", "RUN_STARTDATE"): "2047-01-01",
                        ("AD200", "RUN_REFCASE"): nl.CASES["PRE50"]}[(phase, key)]
            def hist(archive, name):
                phase = name.rsplit("_", 1)[-1]
                a, b = (1997, 2047) if phase == "PRE50" else (2047, 2247)
                return {y: [Path(str(y))] for y in range(a, b)}
            core = SimpleNamespace(env_value=env, history_index=hist,
                                   contiguous=lambda found, start, n: list(range(start, start + n)))
            stages = nl.inspect(core, cases, archive)
            self.assertEqual(len(stages["PRE50"]["years"]), 50)
            self.assertEqual(len(stages["AD200"]["years"]), 200)
            self.assertEqual(len(stages["POST300"]["years"]), 0)
            self.assertIn("absent", stages["POST300"]["issue"])

    def test_ec_uses_only_normal_phase_and_marks_pre_candidate(self):
        stages = {p: {"years": [], "name": nl.CASES[p]} for p, *_ in nl.PHASES}
        stages["PRE50"]["years"] = list(range(1997, 2047))
        stages["AD200"]["years"] = list(range(2047, 2247))
        core = SimpleNamespace(forcing_years=lambda *a: (1997, 2025, 1997),
                               last_complete_cycle=lambda yrs, *a: list(range(1997, 2026)))
        candidates, notes = nl.latest_normal_cycles(core, stages, Path("/cases"), Path("/archive"))
        self.assertEqual([x[0] for x in candidates], ["PRE50"])
        self.assertTrue(any("POST300" in s for s in notes))

    def test_uses_ssh_for_publication(self):
        self.assertEqual(nl.REPO, "git@github.com:lyanyeung/Non-Competition-CLM-experiment.git")

    def test_post_normal_phase_is_preferred_over_pre(self):
        stages = {p: {"years": [], "name": nl.CASES[p]} for p, *_ in nl.PHASES}
        stages["PRE50"]["years"] = list(range(1997, 2047))
        stages["POST300"]["years"] = list(range(2247, 2307))
        core = SimpleNamespace(forcing_years=lambda *a: (1997, 2025, 1997),
                               last_complete_cycle=lambda yrs, *a: yrs[:29])
        candidates, _ = nl.latest_normal_cycles(core, stages, Path("/cases"), Path("/archive"))
        self.assertEqual([x[0] for x in candidates], ["POST300", "PRE50"])


if __name__ == "__main__":
    unittest.main()
