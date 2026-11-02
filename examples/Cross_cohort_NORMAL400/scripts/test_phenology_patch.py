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
