"""Unit tests for 15_needleleaf_final_trials_vs_ec.py (metrics, decision, annual reading)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import test_collapse_diagnostics as tcd   # netCDF4 shim

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("m15", HERE / "15_needleleaf_final_trials_vs_ec.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


class FinalTrialsTest(unittest.TestCase):
    def test_metrics(self):
        m = load()
        yrs = np.arange(1, 101)
        stable = pd.DataFrame({"Year": yrs, "FATES_GPP": np.minimum(yrs / 20, 1) * 4.0, "TLAI": 3.0,
                               "FATES_VEGC_PF": np.minimum(yrs, 60) * 100.0})
        r = m.metrics(stable, 4.0)
        self.assertAlmostEqual(r["GPP_ratio_EC"], 1.0)
        self.assertTrue(r["stable"]); self.assertTrue(r["needleleaf_alive"])
        rising = stable.assign(FATES_GPP=yrs * 0.05)
        r2 = m.metrics(rising, 2.0)
        self.assertFalse(r2["stable"]); self.assertGreater(r2["GPP_ratio_EC"], 2)
        dead = stable.assign(FATES_VEGC_PF=np.where(yrs < 15, 1000.0, 1.0), FATES_GPP=np.where(yrs < 15, 3.0, 0.0))
        self.assertFalse(m.metrics(dead, 4.0)["needleleaf_alive"])

    def test_decide(self):
        m = load()
        rows = []
        for s, d, f in (("A", 1.6, 1.1), ("B", 1.1, 0.9), ("C", 1.0, 0.7)):
            rows += [{"Site": s, "Variant": "control", "Status": "OK", "GPP_ratio_EC": 0.01, "needleleaf_alive": False, "stable": True, "years_read": 100},
                     {"Site": s, "Variant": "D", "Status": "OK", "GPP_ratio_EC": d, "needleleaf_alive": True, "stable": s != "A", "years_read": 100},
                     {"Site": s, "Variant": "F", "Status": "OK", "GPP_ratio_EC": f, "needleleaf_alive": True, "stable": True, "years_read": 100}]
        lines, score = m.decide(rows, ["D", "F"])
        self.assertIn("RECOMMENDED: F", "\n".join(lines))
        self.assertEqual(score["D"]["within25"], 2)
        rows[1].update(Status="INCOMPLETE", years_read=60)
        lines, _ = m.decide(rows, ["D", "F"])
        self.assertIn("INTERIM: 1 trial cases", "\n".join(lines))

    def test_read_year(self):
        m = load()
        with tempfile.TemporaryDirectory() as t:
            paths = []
            for mo in range(1, 13):
                p = Path(t) / f"x.clm2.h0.0001-{mo:02d}.nc"
                tcd.write_nc(p, 1, mo, {"FATES_GPP": ((), [2.0 / 86400000], "kg m-2 s-1"),
                                        "TLAI": ((), [float(mo)], "m2/m2"),
                                        "FATES_VEGC_PF": (("fates_levpft",), [0.0, 1.5, 0.0], "kg m-2"),
                                        "FATES_NPLANT_PF": (("fates_levpft",), [0.0, 0.1, 0.0], "m-2")})
                paths.append(p)
            y = m.read_year(paths)
        self.assertAlmostEqual(y["FATES_GPP"], 2.0, places=6)
        self.assertAlmostEqual(y["FATES_VEGC_PF"], 1500.0)
        self.assertAlmostEqual(y["FATES_NPLANT_PF"], 1000.0)
        self.assertAlmostEqual(y["TLAI"], float(np.sum(np.arange(1, 13) * m.DAYS) / 365), places=6)


if __name__ == "__main__":
    unittest.main()
