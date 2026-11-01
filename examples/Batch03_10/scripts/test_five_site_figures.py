import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_nt_first_with_dt_fallback_in_same_source(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            path = Path(tmp) / "ICOS_FULLSET_HH.csv"
            ts = pd.date_range("2001-01-01", periods=96, freq="30min")
            pd.DataFrame({"TIMESTAMP_START": ts.strftime("%Y%m%d%H%M"),
                          "NEE_VUT_REF": np.ones(96),
                          "GPP_NT_VUT_REF": [20.] * 48 + [-9999.] * 48,
                          "GPP_DT_VUT_REF": [10.] * 96}).to_csv(path, index=False)
            result, _ = figures.ec_daily([path], 2001, 2001, 40)
            self.assertEqual(list(result.EC_GPP_column), [figures.GPP_NT, figures.GPP_DT])
            np.testing.assert_allclose(result.EC_GPP, [20 * figures.EC_TO_GCD, 10 * figures.EC_TO_GCD])

    def test_bad_source_is_recorded_and_does_not_hide_valid_nt_source(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            bad, good = Path(tmp) / "bad.csv", Path(tmp) / "good.csv"
            ts = pd.date_range("2001-01-01", periods=48, freq="30min")
            row = {"TIMESTAMP_START": ts.strftime("%Y%m%d%H%M"),
                   "NEE_VUT_REF": np.ones(48), "GPP_NT_VUT_REF": np.ones(48)}
            pd.DataFrame(row).to_csv(good, index=False)
            row["TIMESTAMP_START"] = ["200101010000"] * 48
            pd.DataFrame(row).to_csv(bad, index=False)
            result, provenance = figures.ec_daily([bad, good], 2001, 2001, 40)
            self.assertEqual(result.EC_GPP_column.iloc[0], figures.GPP_NT)
            self.assertIn("duplicated timestamps", provenance[0]["reason"])

    def test_nt_cut_outweighs_dt_vut_across_sources_and_nee_vut_wins(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            folder = Path(tmp) / "raw" / "package"; folder.mkdir(parents=True)
            a = folder / "EUF_X_FLUXMET_HH.csv"
            b = folder / "FLX_X_FULLSET_HH.csv"
            ts = pd.date_range("2001-01-01", periods=48, freq="30min")
            base = {"TIMESTAMP_START": ts.strftime("%Y%m%d%H%M")}
            pd.DataFrame({**base, "GPP_DT_VUT_REF": np.full(48, 10.),
                          "NEE_VUT_REF": np.full(48, 3.)}).to_csv(a, index=False)
            pd.DataFrame({**base, "GPP_NT_CUT_REF": np.full(48, 20.),
                          "NEE_CUT_REF": np.full(48, 4.)}).to_csv(b, index=False)
            sources = figures.ec_sources(Path(tmp))
            self.assertEqual(len(sources), 2)
            obs, _ = figures.ec_daily(sources, 2001, 2001, 40)
            self.assertEqual(obs.EC_GPP_column.iloc[0], "GPP_NT_CUT_REF")
            self.assertEqual(obs.EC_NEE_column.iloc[0], "NEE_VUT_REF")
            self.assertAlmostEqual(obs.EC_GPP.iloc[0], 20 * figures.EC_TO_GCD)
            self.assertAlmostEqual(obs.EC_NEE.iloc[0], 3 * figures.EC_TO_GCD)

    def test_cut_only_source_is_not_excluded(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            folder = Path(tmp) / "raw" / "release"; folder.mkdir(parents=True)
            path = folder / "EUF_DE-Lnf_FLUXMET_HH.csv"
            ts = pd.date_range("2001-01-01", periods=48, freq="30min")
            pd.DataFrame({"TIMESTAMP_START": ts.strftime("%Y%m%d%H%M"),
                          "NEE_CUT_REF": np.ones(48), "GPP_NT_CUT_REF": np.ones(48)}).to_csv(path, index=False)
            obs, _ = figures.ec_daily(figures.ec_sources(Path(tmp)), 2001, 2001, 40)
            self.assertEqual(obs.EC_GPP_column.iloc[0], "GPP_NT_CUT_REF")
            self.assertEqual(obs.EC_NEE_column.iloc[0], "NEE_CUT_REF")

    def test_phase_alignment_for_cycle_comparisons(self):
        years = np.arange(2400, 2410)
        # Alignment 2402, forcing length 3: 2402-04 and 2405-07.
        vals = [99, 99, 1, 2, 3, 2, 3, 4, 99, 99]
        df = pd.DataFrame({"Phase": "NORMAL", "ModelYear": years, "x": vals})
        out = figures.convergence(df, ["x"], {"x": {"csv_units": "g C m-2"}}, 3, 2402)
        self.assertEqual(out.iloc[0].Normal_complete_cycles, 2)
        self.assertAlmostEqual(out.iloc[0].Last_two_aligned_cycles_mean_abs_change_pct, 50.)
        self.assertAlmostEqual(out.iloc[0].Last_two_aligned_cycles_mean_change_pct, 50.)
        self.assertEqual(out.iloc[0].Last_aligned_cycle_start_model_year, 2405)

    def test_short_normal_phase_has_no_full_window_trend(self):
        self.assertTrue(np.isnan(figures.trend(np.arange(99.), 100)[0]))
        self.assertTrue(np.isnan(figures.trend(np.arange(29.), 30)[0]))

    def test_ad_diagnostics_exclude_normal_phase_and_align_cycles(self):
        frame = pd.DataFrame({"SpinupYear": np.arange(1, 801),
                              "ModelYear": np.arange(2000, 2800),
                              "Phase": ["AD"] * 400 + ["NORMAL"] * 400,
                              "TOTSOMC": np.r_[np.arange(400.) + 10, np.full(400, 100000.)]})
        d = figures.ad_diagnostics(frame, ["TOTSOMC"], 10, 2000).iloc[0]
        self.assertAlmostEqual(d.Last100y_slope_per_year, 1.)
        self.assertEqual(d.AD_complete_cycles, 40)
        self.assertAlmostEqual(d.Last_two_aligned_AD_cycle_mean_change_pct, 1000 / 394.5)

    def test_ad_figure_is_written(self):
        spin = np.arange(1, 801)
        data = pd.DataFrame({"SpinupYear": spin, "ModelYear": spin + 1999,
                             "Phase": np.where(spin <= 400, "AD", "NORMAL"), "TOTSOMC": spin * 1.})
        meta = {"TOTSOMC": {"plot_units": "g C m-2", "csv_units": "g C m-2"}}
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            fig = figures.plot_ad_panels(data, ["TOTSOMC"], meta, "TEST", Path(tmp), 10, 2000)
            self.assertTrue(fig.is_file())
            self.assertTrue((Path(tmp) / "TEST_AD_diagnostics.csv").is_file())

    def test_normal_metrics_ignore_ad_and_plots_do_not_join_phases(self):
        from matplotlib.axes import Axes
        ad = pd.DataFrame({"Phase": "AD", "ModelYear": np.arange(2000, 2400),
                           "SpinupYear": np.arange(1, 401), "TOTSOMC": np.full(400, 1.)})
        normal = pd.DataFrame({"Phase": "NORMAL", "ModelYear": np.arange(2400, 2800),
                               "SpinupYear": np.arange(401, 801), "TOTSOMC": np.arange(400.) + 1000})
        df = pd.concat([ad, normal], ignore_index=True)
        meta = {"TOTSOMC": {"csv_units": "g C m-2", "plot_units": "g C m-2"}}
        conv = figures.convergence(df, ["TOTSOMC"], meta, 10, 2000)
        self.assertAlmostEqual(conv.iloc[0].Last100y_slope_per_year, 1.)
        original = Axes.plot
        calls = []
        def record(ax, x, y, *args, **kwargs):
            calls.append((np.asarray(x), np.asarray(y)))
            return original(ax, x, y, *args, **kwargs)
        with tempfile.TemporaryDirectory(dir=HERE) as tmp, patch.object(Axes, "plot", record):
            overview = figures.plot_overview(df, ["TOTSOMC"], meta, "TEST", "AD → Normal", Path(tmp), False)
            panels = figures.plot_panels(df, ["TOTSOMC"], meta, "TEST", Path(tmp), False, conv, 10)
            self.assertTrue(overview.is_file())
            self.assertTrue(panels.is_file())
        self.assertEqual([(x.min(), x.max()) for x, _ in calls], [(1, 400), (401, 800), (401, 800)])

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

