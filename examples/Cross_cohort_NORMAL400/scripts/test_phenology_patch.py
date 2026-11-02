"""Test the FATES phenology backport in 17_phenology_patch_rerun.py on a minimal EDPhysiologyMod-like source."""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = """module EDPhysiologyMod
  use FatesInterfaceTypesMod, only    : hlm_use_fixed_biogeog
  use FatesConstantsMod     , only : itrue,ifalse
contains
  subroutine phenology
    integer  :: ncdstart          ! beginning of counting period for chilling degree days.
    integer  :: gddstart          ! beginning of counting period for growing degree days.

    !   preventing them from competing

    if ( any(currentSite%cstatus == [phen_cstat_iscold,phen_cstat_nevercold]) .and. &
         (currentSite%grow_deg_days > gdd_threshold) .and. &
         (currentSite%cndaysleafoff > ED_val_phen_mindayson) .and. &
         (currentSite%nchilldays >= 1)) then
       currentSite%cstatus = phen_cstat_notcold  ! Set to not-cold status (leaves can come on)
    endif !GDD
    if( (currentSite%cstatus == phen_cstat_notcold)  .and. &
        (currentSite%cndaysleafoff > 400)) then   ! remove leaves after a whole year,
       currentSite%grow_deg_days  = 0._r8
       currentSite%cstatus = phen_cstat_nevercold  ! alter status of site to imply that this
    endif
  end subroutine phenology
end module EDPhysiologyMod
"""


def load():
    spec = importlib.util.spec_from_file_location("m17", HERE / "17_phenology_patch_rerun.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.load09()
    return m


class PhenologyPatchTest(unittest.TestCase):
    def test_patch(self):
        m = load()
        p = m.patch_source(SRC)
        self.assertIn("integer  :: nchill_threshold", p)
        self.assertIn("if(hlm_use_fixed_biogeog .eq. ifalse)then", p)
        self.assertIn("(currentSite%nchilldays >= nchill_threshold)) then", p)
        self.assertIn("currentSite%cstatus = phen_cstat_iscold  ! alter status", p)
        self.assertNotIn("cstatus = phen_cstat_nevercold", p)
        self.assertNotIn("nchilldays >= 1", p)
        # the block sits right before the leaf-on IF, inside the subroutine
        self.assertLess(p.index("nchill_threshold=0"), p.index("if ( any(currentSite%cstatus"))
        self.assertTrue(all(len(l) <= 132 for l in p.splitlines()))

    def test_hide_spinup_state(self):
        m = load()
        txt = "use_fates = .true.\n spinup_state = 2\nSPINUP_STATE=1 ! x\nhist_nhtfrq = 0\n"
        new, n = m.hide_spinup_state(txt)
        self.assertEqual(n, 2)
        self.assertNotIn("\n spinup_state = 2", "\n" + new.replace(m.BUILD_TAG, "#"))
        self.assertIn(m.BUILD_TAG + " spinup_state = 2", new)
        self.assertIn("hist_nhtfrq = 0", new)
        self.assertEqual(m.hide_spinup_state("hist_nhtfrq = 0\n"), ("hist_nhtfrq = 0\n", 0))


    def test_compile_evidence(self):
        import gzip, tempfile, time
        m = load()
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "cmake-bld" / "x").mkdir(parents=True)
            (d / "cmake-bld" / "x" / "EDPhysiologyMod.F90.o").write_text("o")
            own = "ifort -c /iridisfs/scratch/u/cases/CASE_PHENFIX50/SourceMods/src.clm/EDPhysiologyMod.F90"
            (d / "lnd.bldlog.1").write_bytes(gzip.compress(own.encode()))
            ok, msg = m.compile_evidence(d, "CASE_PHENFIX50", time.time() - 100)
            self.assertTrue(ok, msg)
            time.sleep(0.01)
            bad = "ifort -c /x/CTSM/src/fates/biogeochem/EDPhysiologyMod.F90"
            (d / "lnd.bldlog.2").write_bytes(gzip.compress(bad.encode()))
            ok, msg = m.compile_evidence(d, "CASE_PHENFIX50", time.time() - 100)
            self.assertFalse(ok)
            self.assertIn("SHARED", msg)
            (d / "lnd.bldlog.3").write_text("nothing recompiled")   # incremental rebuild: decided by bldlog.2
            self.assertFalse(m.compile_evidence(d, "CASE_PHENFIX50", 0)[0])
            (d / "lnd.bldlog.2").unlink()
            self.assertTrue(m.compile_evidence(d, "CASE_PHENFIX50", 0)[0])
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(m.compile_evidence(d, "CASE_PHENFIX50", 0)[0])

    def test_refuses(self):
        m = load()
        with self.assertRaises(RuntimeError):
            m.patch_source(m.patch_source(SRC))                      # already patched
        with self.assertRaises(RuntimeError):
            m.patch_source(SRC.replace("(currentSite%nchilldays >= 1)) then", "(currentSite%nchilldays >= 2)) then"))
        with self.assertRaises(RuntimeError):
            m.patch_source(SRC + SRC.split("contains")[1])            # anchors twice
        with self.assertRaises(RuntimeError):
            m.patch_source(SRC.replace("itrue,ifalse", "itrue"))       # ifalse not imported


if __name__ == "__main__":
    unittest.main()
