"""Test the parameter-copy logic of 13_needleleaf_param_trials.py (no CIME needed)."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FATES_DEFAULT = Path("/tmp/fates/parameter_files/fates_params_default.json")


def fake_params(path):
    path.write_text(json.dumps({"attributes": {"x": 1}, "dimensions": {"fates_pft": 3}, "parameters": {
        "fates_pftname": {"dims": ["fates_pft"], "data": ["bet", "needleleaf_evergreen_extratrop_tree", "bdt"]},
        "fates_alloc_storage_cushion": {"dims": ["fates_pft"], "units": "fraction", "data": [1.2, 1.2, 2.4]},
        "fates_mort_upthresh_cstarvation": {"dims": ["fates_pft"], "data": [1.0, 1.0, 1.0]},
        "fates_leaf_slatop": {"dims": ["fates_pft"], "data": [0.012, 0.005, 0.03]},
        "fates_leaf_vcmax25top": {"dims": ["fates_leafage_class", "fates_pft"], "data": [[50, 62, 58]]},
        "fates_grperc": {"dims": ["fates_pft"], "data": [0.11, 0.11, 0.11]}}}))


class ParamTrialTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        spec = importlib.util.spec_from_file_location("trial13", HERE / "13_needleleaf_param_trials.py")
        self.m = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.m)
        self.m.load09()
        self.m.PARAM_DIR = Path(self.tmp.name) / "params"

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, base):
        src = json.loads(base.read_text())["parameters"]
        for v, (_, changes, nml) in self.m.VARIANTS.items():
            if not changes:
                with self.assertRaises(RuntimeError):
                    self.m.make_param(base, v)
                continue
            out, sha, rec = self.m.make_param(base, v)
            new = json.loads(out.read_text())["parameters"]
            for k in src:
                if k not in changes:
                    self.assertEqual(src[k], new[k], k)
            for k, val in changes.items():
                a, b = np.asarray(src[k]["data"], float), np.asarray(new[k]["data"], float)
                self.assertTrue(np.allclose(b[..., 1], val))
                self.assertTrue(np.array_equal(np.delete(a, 1, axis=-1), np.delete(b, 1, axis=-1)))
            receipt = json.loads(Path(str(out) + ".receipt.json").read_text())
            self.assertEqual(receipt["sha256"], sha)
            out2, sha2, _ = self.m.make_param(base, v)          # idempotent: same file, no rewrite
            self.assertEqual(sha2, sha)
        return out

    def test_fake(self):
        base = Path(self.tmp.name) / "p.json"; fake_params(base)
        self.check(base)

    @unittest.skipUnless(FATES_DEFAULT.is_file(), "FATES default parameter file not available")
    def test_real_default(self):
        base = Path(self.tmp.name) / "fates_params_default.json"; shutil.copy(FATES_DEFAULT, base)
        self.check(base)

    def test_refuses_wrong_pft(self):
        base = Path(self.tmp.name) / "p.json"; fake_params(base)
        d = json.loads(base.read_text()); d["parameters"]["fates_pftname"]["data"][1] = "c3_grass"; base.write_text(json.dumps(d))
        with self.assertRaises(RuntimeError):
            self.m.make_param(base, "A")

    def test_refuses_overwrite_of_different_file(self):
        base = Path(self.tmp.name) / "p.json"; fake_params(base)
        out, _, _ = self.m.make_param(base, "A")
        out.write_text(out.read_text().replace("2.4", "9.9"))
        with self.assertRaises(RuntimeError):
            self.m.make_param(base, "A")

    def test_variant_e_is_namelist_only(self):
        desc, p, n = self.m.VARIANTS["E"]
        self.assertEqual(p, {}); self.assertEqual(n, {"use_fates_dbh_init": ".true."})
        txt = "use_fates_dbh_init = .false.\nhist_mfilt = 12\n"
        new = self.m.set_nml(txt, "use_fates_dbh_init", ".true.")
        self.assertEqual(new.count("use_fates_dbh_init"), 1); self.assertIn("use_fates_dbh_init = .true.", new)

    def test_set_paramfile(self):
        txt = "fsurdat = '/s.nc'\nfates_paramfile = '/old.json'\nhist_mfilt = 12\n"
        new = self.m.set_paramfile(txt, Path("/new.json"))
        self.assertEqual(new.count("fates_paramfile"), 1)
        self.assertIn("fates_paramfile = '/new.json'", new)
        self.assertIn("fsurdat = '/s.nc'", new); self.assertIn("hist_mfilt = 12", new)


if __name__ == "__main__":
    unittest.main()
