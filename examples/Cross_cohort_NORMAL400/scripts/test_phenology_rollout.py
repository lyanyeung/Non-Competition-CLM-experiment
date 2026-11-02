"""Test 22_phenology_patch_rollout.py: cold-deciduous share from PCT_NAT_PFT + fates_hlm_pft_map + season_decid."""
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
        self.m = mod("m22", "22_phenology_patch_rollout.py")
        self.m.T = mod("m13", "13_needleleaf_param_trials.py")

    def params(self):
        names = ["broadleaf_evergreen_tropical_tree", "needleleaf_evergreen_extratrop_tree",
                 "needleleaf_colddecid_extratrop_tree", "broadleaf_colddecid_extratrop_tree", "c4_grass"]
        mp = [[0, 1, 0, 0, 0], [0, 1, 0, 0, 0], [0, 0, 1, 0, 0], [1, 0, 0, 0, 0], [0, 0, 0, 1, 0], [0, 0, 0, 0, 1]]
        return {"parameters": {"fates_pftname": {"dims": ["fates_pft"], "data": names},
                               "fates_phen_season_decid": {"dims": ["fates_pft"], "data": [0, 0, 1, 1, 0]},
                               "fates_hlm_pft_map": {"dims": ["fates_hlm_pftno", "fates_pft"], "data": mp}}}

    def test_share(self):
        #        bare NETt NETb NDT BET BDT C4
        pct = [10, 54, 0, 9, 0, 27, 0]
        s, present = self.m.decid_share(pct, self.params())
        self.assertAlmostEqual(s, 40.0)                       # (9 + 27) / 90
        self.assertEqual([n for n, _ in present], ["needleleaf_colddecid_extratrop_tree", "broadleaf_colddecid_extratrop_tree"])
        self.assertEqual(self.m.decid_share([0, 100, 0, 0, 0, 0, 0], self.params())[0], 0.0)

    def test_leaf_habit(self):
        p = self.params(); del p["parameters"]["fates_phen_season_decid"]
        p["parameters"]["fates_phen_leaf_habit"] = {"dims": ["fates_pft"], "data": [1, 1, 2, 1, 2]}   # 2 = cold deciduous
        self.assertAlmostEqual(self.m.decid_share([10, 54, 0, 9, 0, 27, 0], p)[0], 40.0)
        p["parameters"]["fates_phen_leaf_habit"]["data"] = [1, 1, 3, 1, 3]                           # 3 = stress deciduous
        self.assertEqual(self.m.decid_share([10, 54, 0, 9, 0, 27, 0], p)[0], 0.0)

    def test_missing_param(self):
        p = self.params(); del p["parameters"]["fates_phen_season_decid"]
        with self.assertRaises(ValueError):
            self.m.decid_share([0, 100, 0, 0, 0, 0, 0], p)

    def test_site_lists(self):
        m20 = mod("m20", "20_needleleaf_rerun_AD400_NORMAL400.py")
        self.assertEqual(len(m20.SITES) + len(self.m.OTHER), 75)
        self.assertFalse(set(m20.SITES) & set(self.m.OTHER))


if __name__ == "__main__":
    unittest.main()
