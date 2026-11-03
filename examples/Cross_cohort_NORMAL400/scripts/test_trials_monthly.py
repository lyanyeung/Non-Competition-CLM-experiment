"""Test 19_needleleaf_trials_monthly_vs_ec.py on synthetic monthly series: metrics, seasonal cycle, plots, summary."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("m19", HERE / "19_needleleaf_trials_monthly_vs_ec.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def synthetic():
    d = pd.date_range("2010-01-01", "2012-12-01", freq="MS")
    season = np.clip(np.sin((d.month - 3) / 12 * 2 * np.pi), 0, None)
    ec = 5 * season
    mon = pd.DataFrame({"date": d, "EC_GPP": ec, "EC_NEE": -0.8 * ec + 0.5,
                        "control_GPP": 0.02 * season, "control_NEE": 0.0 * season,
                        "D_GPP": 1.2 * ec, "D_NEE": -0.1 * ec, "F_GPP": 1.1 * ec, "F_NEE": -0.1 * ec})
    mon.loc[5, "EC_GPP"] = np.nan          # a month without EC data
    return mon


class T(unittest.TestCase):
    def test_metrics_and_seasonal(self):
        m = load(); mon = synthetic()
        sc = m.metrics(mon, "GPP", "F_GPP")
        self.assertEqual(sc["N"], 35)
        self.assertAlmostEqual(sc["Ratio"], 1.1, places=6)
        self.assertGreater(sc["R2"], 0.9)
        c = m.seasonal(mon.dropna(subset=["EC_GPP"]), "F_GPP")
        self.assertEqual(len(c), 12)
        self.assertTrue(np.isfinite(c).all())

    def test_plots_and_summary(self):
        m = load(); mon = synthetic()
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            p = m.plot_site("XX-Tst", mon, {"gpp": "GPP_NT_VUT_REF"}, 2010, 2012, [2001, 2003], d)
            self.assertTrue(p.is_file() and p.stat().st_size > 10000)
            for flux in ("GPP", "NEE"):
                self.assertTrue(m.plot_seasonal({"XX-Tst": mon, "YY-Tst": mon}, flux, d).is_file())
        rows = [{"Site": "XX-Tst", "Case": v, "Flux": f, "Status": "OK", **m.metrics(mon, f, f"{v}_{f}")}
                for v in ("control", "D", "F") for f in ("GPP", "NEE")]
        s = "\n".join(m.summarize(rows))
        self.assertIn("median model/EC 1.10", s)
        self.assertIn("control", s)


if __name__ == "__main__":
    unittest.main()
