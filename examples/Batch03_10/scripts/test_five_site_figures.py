import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("figures", HERE / "15_plot_AD400_NORMAL400_convergence_and_EC.py")
figures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(figures)


class TestScienceGuards(unittest.TestCase):
    def test_nt_preferred_across_sources_and_dates(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            dt = Path(tmp) / "ICOS_DT.csv"
            nt = Path(tmp) / "FLX_NT.csv"
            a = pd.date_range("2001-01-01", periods=96, freq="30min")
            base = {"TIMESTAMP_START": a.strftime("%Y%m%d%H%M"), "NEE_VUT_REF": np.ones(96)}
            pd.DataFrame({**base, "GPP_DT_VUT_REF": np.full(96, 10.)}).to_csv(dt, index=False)
            pd.DataFrame({**base, "GPP_NT_VUT_REF": [20.] * 48 + [-9999.] * 48}).to_csv(nt, index=False)
            result, prov = figures.ec_daily([dt, nt], 2001, 2001, 40)
            self.assertEqual(list(result.EC_GPP_column), [figures.GPP_NT, figures.GPP_DT])
            self.assertEqual(list(result.EC_GPP_source), [nt.name, dt.name])
            np.testing.assert_allclose(result.EC_GPP, [20 * figures.EC_TO_GCD, 10 * figures.EC_TO_GCD])
            self.assertEqual(len(prov), 2)

    def test_phase_alignment_for_cycle_comparisons(self):
        years = np.arange(2400, 2410)
        # Alignment 2402, forcing length 3: 2402-04 and 2405-07.
        vals = [99, 99, 1, 2, 3, 2, 3, 4, 99, 99]
        df = pd.DataFrame({"Phase": "NORMAL", "ModelYear": years, "x": vals})
        out = figures.convergence(df, ["x"], {"x": {"csv_units": "g C m-2"}}, 3, 2402)
        self.assertEqual(out.iloc[0].Normal_complete_cycles, 2)
        self.assertAlmostEqual(out.iloc[0].Last_two_aligned_cycles_mean_abs_change_pct, 50.)

    def test_latest_full_cycle_respects_phase(self):
        self.assertEqual(figures.last_complete_cycle(list(range(2400, 2410)), 2000, 2002, 2402), [2405, 2406, 2407])
        with self.assertRaises(ValueError):
            figures.last_complete_cycle([2400, 2401], 2000, 2002, 2402)

    def test_monthly_uses_same_valid_days(self):
        d = pd.DataFrame({"date": pd.date_range("2001-01-01", periods=25),
                          "obs": [1.] * 20 + [np.nan] * 5,
                          "model": [2.] * 20 + [100.] * 5})
        row = figures.monthly(d, "obs", "model", 20).iloc[0]
        self.assertEqual(row["model"], 2.)
        self.assertEqual(row["obs_NDAY"], 20)

    def test_hourly_sources_use_equivalent_twenty_hours(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            path = Path(tmp) / "AMF_X_FLUXMET_HR.csv"
            ts = pd.date_range("2001-01-01", periods=24, freq="h")
            pd.DataFrame({"TIMESTAMP_START": ts.strftime("%Y%m%d%H%M"),
                          "NEE_VUT_REF": np.ones(24), "GPP_NT_VUT_REF": np.ones(24)}).to_csv(path, index=False)
            data, prov = figures.ec_daily([path], 2001, 2001, 40)
            self.assertEqual(prov[0]["sample_interval_seconds"], 3600)
            self.assertTrue(np.isfinite(data.EC_GPP.iloc[0]))

    def test_lai_is_not_a_carbon_pool(self):
        self.assertNotIn("TLAI", figures.CANDIDATES)

    def test_runtime_normal_stream_takes_precedence(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            case = Path(tmp) / "case"
            run = Path(tmp) / "run"
            (case / "CaseDocs").mkdir(parents=True)
            run.mkdir()
            def stream(first, last, align):
                return (f'<streams><stream name="CLM_USRDAT"><year_first>{first}</year_first>'
                        f'<year_last>{last}</year_last><year_align>{align}</year_align></stream></streams>')
            (case / "CaseDocs" / "datm.streams.xml").write_text(stream(2000, 2010, 2000))
            (run / "datm.streams.xml").write_text(stream(2001, 2020, 2001))
            self.assertEqual(figures.forcing_years(case, run), (2001, 2020, 2001))


if __name__ == "__main__":
    unittest.main()

