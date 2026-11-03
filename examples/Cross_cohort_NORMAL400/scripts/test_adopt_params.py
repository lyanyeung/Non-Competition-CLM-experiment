"""Test 18_adopt_needleleaf_params.py: PFT-2 share from PCT_NAT_PFT + fates_hlm_pft_map, and the adopted change."""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def mod(name, fn):
    spec = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class T(unittest.TestCase):
    def setUp(self):
        self.m = mod("m18", "18_adopt_needleleaf_params.py")
        self.t13 = mod("m13", "13_needleleaf_param_trials.py")
        self.m.T = self.t13

    def params(self, with_map=True):
        names = ["broadleaf_evergreen_tropical_tree", "needleleaf_evergreen_extratrop_tree",
                 "needleleaf_colddecid_extratrop_tree", "broadleaf_colddecid_extratrop_tree"]
        p = {"parameters": {"fates_pftname": {"dims": ["fates_pft"], "data": names}}}
        if with_map:   # HLM PFTs 1..5 (rows) -> FATES PFTs (cols); dims as in the FATES json
            mp = [[0, 1, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]]
            p["parameters"]["fates_hlm_pft_map"] = {"dims": ["fates_hlm_pftno", "fates_pft"], "data": mp}
        return p

    def test_share_with_map(self):
        pct = [20, 30, 10, 0, 0, 40]           # bare 20; NET temperate 30, NET boreal 10, BDT 40
        s, how = self.m.pft2_share(pct, self.params())
        self.assertAlmostEqual(s, 50.0)        # (30+10)/80
        self.assertIn("fates_hlm_pft_map", how)
        self.assertEqual(self.m.pft2_share([100, 0, 0, 0, 0, 0], self.params())[0], 0.0)
        self.assertEqual(self.m.pft2_share([0, 0, 0, 0, 0, 100], self.params())[0], 0.0)

    def test_share_without_map(self):
        s, how = self.m.pft2_share([0, 25, 25, 0, 0, 50], self.params(False))
        self.assertAlmostEqual(s, 50.0)
        self.assertIn("CLM natpft", how)

    def test_read_pct(self):
        try:
            import netCDF4
        except ImportError:
            self.skipTest("netCDF4 not installed")
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "surf.nc"
            with netCDF4.Dataset(f, "w") as ds:
                ds.createDimension("natpft", 3); ds.createDimension("lsmlat", 1); ds.createDimension("lsmlon", 1)
                v = ds.createVariable("PCT_NAT_PFT", "f8", ("natpft", "lsmlat", "lsmlon"))
                v[:] = [[[10.0]], [[60.0]], [[30.0]]]
            self.assertEqual(self.m.read_pct(f), [10.0, 60.0, 30.0])

    def test_decision_matches_variant_F(self):
        self.assertEqual(self.t13.VARIANTS["F"][1], self.m.CHANGES)
        self.assertEqual(self.m.CHANGES, {"fates_alloc_storage_cushion": 2.4, "fates_leaf_slatop": 0.008})


if __name__ == "__main__":
    unittest.main()
