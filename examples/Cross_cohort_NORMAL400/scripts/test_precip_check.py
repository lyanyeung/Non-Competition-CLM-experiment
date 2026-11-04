"""Tests for 32_precip_check_tower_forcing_MAP.py on synthetic tower, BIF and forcing files.

netCDF4 is replaced by a small stub so the test also runs where netCDF4 is not installed.
"""
import contextlib
import csv
import importlib.util
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FORCING = {}  # path -> (time values in days since 2001-01-01, PRECTmms)


class _Var:
    def __init__(self, data, **attrs):
        self._d = np.asarray(data)
        self.__dict__.update(attrs)

    def __getitem__(self, k):
        return self._d[k]

    def __len__(self):
        return len(self._d)


class _Dataset:
    def __init__(self, path):
        t, p = FORCING[str(path)]
        self.variables = {"time": _Var(t, units="days since 2001-01-01 00:00:00", calendar="noleap"),
                          "PRECTmms": _Var(p.reshape(-1, 1, 1))}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _noleap(v, units, calendar="standard"):  # 365-day years from 2001
    return [types.SimpleNamespace(year=2001 + int(float(x) // 365)) for x in v]


sys.modules.setdefault("netCDF4", types.SimpleNamespace(Dataset=_Dataset, num2date=_noleap))

spec = importlib.util.spec_from_file_location("pc32", HERE / "32_precip_check_tower_forcing_MAP.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def write_tower(path: Path, years, p_hh: float, le: float, qc2: bool):
    idx = pd.date_range(f"{years[0]}-01-01", f"{years[-1] + 1}-01-01", freq="30min", inclusive="left")
    idx = idx[~((idx.month == 2) & (idx.day == 29))]
    df = pd.DataFrame({"TIMESTAMP_START": idx.strftime("%Y%m%d%H%M"),
                       "P_F": p_hh, "P_F_QC": 2 if qc2 else 0, "P_ERA": p_hh, "LE_F_MDS": le})
    df.to_csv(path, index=False)


class PrecipCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sites, self.cases, self.out = self.tmp / "sites", self.tmp / "cases", self.tmp / "out"
        raw = self.sites / "US-UiD" / "forcing" / "raw_v1"
        raw.mkdir(parents=True)
        # 0.2 mm per half hour = 3504 mm/yr; LE 40 W m-2 -> ~515 mm/yr ET
        write_tower(raw / "AMF_US-UiD_FLUXNET_FLUXMET_HH_2001-2002_v1.csv", [2001, 2002], 0.2, 40.0, True)
        with (raw / "AMF_US-UiD_FLUXNET_BIF_2001-2002_v1.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["SITE_ID", "GROUP_ID", "VARIABLE_GROUP", "VARIABLE", "DATAVALUE"])
            w.writerow(["US-UiD", "1", "GRP_CLIM_AVG", "MAP", "950"])
        # forcing scaled to MAP: 950 mm/yr in hourly steps over two 365-day years
        fdir = self.tmp / "forcing_shadow"
        fdir.mkdir()
        files = []
        for k, yy in enumerate((2001, 2002)):
            t = k * 365 + np.arange(365 * 24) / 24.0
            pr = np.full(t.size, 950.0 / (365 * 86400))
            fp = fdir / f"{yy}.nc"
            fp.write_bytes(b"")
            FORCING[str(fp)] = (t, pr)
            files.append(fp)
        case = self.cases / "US-UiD_FATES_AD400"
        (case / "CaseDocs").mkdir(parents=True)
        (case / "CaseDocs" / "datm.streams.xml").write_text(
            "<file id='stream' version='2.0'><stream_info name='CLM1PT.precip'><datafiles>"
            + "".join(f"<file>{p}</file>" for p in files)
            + "</datafiles><datavars><var>PRECTmms Faxa_precn</var></datavars></stream_info></file>")

    def run32(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = M.main(["--sites", "US-UiD", "--sites-root", str(self.sites), "--cases", str(self.cases),
                         "--outputs", str(self.out), "--out", str(self.tmp / "o.csv"), *args])
        self.assertEqual(rc, 0)
        with (self.tmp / "o.csv").open() as f:
            return buf.getvalue(), list(csv.DictReader(f))

    def test_tower_high_forcing_corrected(self):
        text, rows = self.run32("--per-year")
        r = rows[0]
        self.assertEqual(r["tower_verdict"], "TOWER_P_HIGH")
        self.assertEqual(r["forcing_verdict"], "OK")
        self.assertAlmostEqual(float(r["MAP_mm"]), 950.0)
        self.assertAlmostEqual(float(r["tower_P_F_mm"]), 3504.0, delta=1)
        self.assertAlmostEqual(float(r["forcing_P_mm"]), 950.0, delta=1)
        self.assertAlmostEqual(float(r["era_filled_pct"]), 100.0)
        self.assertEqual(r["cases"], "US-UiD_FATES_AD400")
        self.assertIn("2002", text)

    def test_map_override_and_no_forcing(self):
        _, rows = self.run32("--map", "US-UiD=3500", "--no-forcing")
        self.assertEqual(rows[0]["tower_verdict"], "OK")
        self.assertEqual(rows[0]["forcing_verdict"], "not read")
        self.assertEqual(rows[0]["MAP_source"], "--map")

    def test_verdicts(self):
        self.assertEqual(M.verdict(200.0, 300.0, "TOWER"), "TOWER_P_LOW")
        self.assertEqual(M.verdict(300.0, float("nan"), "TOWER"), "NO_MAP")
        self.assertEqual(M.verdict(float("nan"), 300.0, "TOWER"), "")


if __name__ == "__main__":
    unittest.main()
