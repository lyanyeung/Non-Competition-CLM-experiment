"""Test 16_dbf_collapse_monthly.py: leaves kept into the last winter, storage exhausted, collapse detected."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np

import test_collapse_diagnostics as tcd

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("m16", HERE / "16_dbf_collapse_monthly.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def month_values(y, mo, collapse=None, keep_leaves_year=None):
    dead = collapse is not None and y >= collapse
    summer = mo in (5, 6, 7, 8, 9)
    leaf = 0.1 if summer else 0.0
    if keep_leaves_year is not None and (y == keep_leaves_year and mo >= 10 or y == keep_leaves_year + 1 and mo <= 3):
        leaf = 0.1
    store = 0.05 if not summer else 0.1
    if keep_leaves_year is not None and (y == keep_leaves_year and mo >= 10 or y == keep_leaves_year + 1 and mo <= 3):
        store = max(0.0, 0.05 - 0.01 * ((mo - 9) if mo >= 10 else (mo + 3)))
    if dead:
        leaf = store = 0.0
    dleafon = (mo - 5) * 30 if mo >= 5 else (mo + 7) * 30
    return {"FATES_GPP": ((), [(5.0 if summer and not dead else 0.0) / 86400000], "kg m-2 s-1"),
            "TSA": ((), [285.0 if summer else 270.0], "K"),
            "FATES_DAYSINCE_COLDLEAFON": ((), [float(dleafon)], "days"),
            "FATES_LEAFC_PF": (("fates_levpft",), [0.0, leaf, 0.0], "kg m-2"),
            "FATES_STOREC_PF": (("fates_levpft",), [0.0, store, 0.0], "kg m-2"),
            "FATES_STOREC_TF_PF": (("fates_levpft",), [0.0, store / 0.1, 0.0], "1"),
            "FATES_VEGC_PF": (("fates_levpft",), [0.0, 0.0 if dead else 5.0, 0.0], "kg m-2"),
            "FATES_NPLANT_PF": (("fates_levpft",), [0.0, 0.0 if dead else 0.5, 0.0], "m-2"),
            "FATES_LEAF_MAINT_RESP": ((), [(leaf * 2) / 86400000], "kg m-2 s-1")}


class DbfCollapseTest(unittest.TestCase):
    def test_end_to_end(self):
        m = load()
        with tempfile.TemporaryDirectory() as t:
            arch = Path(t) / "archive"
            for case, years, kw in (("TGT_DIAG", 12, dict(collapse=10, keep_leaves_year=8)), ("REF", 6, {})):
                h = arch / case / "lnd" / "hist"; h.mkdir(parents=True)
                for y in range(1, years + 1):
                    for mo in range(1, 13):
                        tcd.write_nc(h / f"{case}.clm2.h0.{y:04d}-{mo:02d}.nc", y, mo, month_values(y, mo, **kw))
            out = Path(t) / "out"
            rc = m.main(["--output-root", str(out), "--allow-scratch-output", "--archive-root", str(arch), "--pft", "2",
                         "--cases", "TGT:TGT_DIAG", "--reference", "REF_ref:REF", "--years", "12", "--ref-years", "4"])
            self.assertEqual(rc, 0)
            txt = (out / "dbf_collapse_findings.txt").read_text()
            self.assertIn("TGT: collapse year 10", txt)
            self.assertIn("LEAVES KEPT INTO WINTER", txt)
            self.assertIn("storage exhausted", txt)
            self.assertIn("REFERENCE", txt)
            self.assertTrue((out / "TGT" / "TGT_16_monthly_window.png").is_file())


if __name__ == "__main__":
    unittest.main()
