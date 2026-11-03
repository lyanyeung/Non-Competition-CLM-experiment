"""Test 21_fix_humanindex_rerun.py naming and user_nl editing with module 09's namelist helpers."""
import importlib.util
import types
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
        self.m = mod("m21", "21_fix_humanindex_rerun.py")
        r09 = mod("m09", "09_clone_AD_diag_rerun.py")
        self.m.R = types.SimpleNamespace(CASES=Path("/c"), OUT=Path("/o"), nml_blocks=r09.nml_blocks, fail=r09.fail)

    def test_names(self):
        i = self.m.ident("US-Aud_AMF_B01SIX_FIXNC_AD400_DIRECT")
        self.assertEqual(i["ad"], "US-Aud_AMF_B01SIX_FIXNC_AD400_DIRECT_HINONE")
        self.assertEqual(i["n"], "US-Aud_AMF_B01SIX_FIXNC_NORMAL400_DIRECT_HINONE")
        self.assertEqual(i["n_arch"], Path("/o/archive/US-Aud_AMF_B01SIX_FIXNC_NORMAL400_DIRECT_HINONE"))
        with self.assertRaises(RuntimeError):
            self.m.ident("US-Aud_NORMAL400")

    def test_drop_spinup_state(self):
        t = "use_fates = .true.\nspinup_state = 2\nhist_fincl1 = 'A',\n  'B'\ncalc_human_stress_indices = 'NONE'\n"
        out = self.m.drop_key(t, "spinup_state")
        self.assertNotIn("spinup_state", out)
        self.assertIn("hist_fincl1 = 'A',\n  'B'\n", out)
        self.assertIn("calc_human_stress_indices = 'NONE'", out)


if __name__ == "__main__":
    unittest.main()
