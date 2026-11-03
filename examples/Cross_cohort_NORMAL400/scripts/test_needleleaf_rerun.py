"""Test 20_needleleaf_rerun_AD400_NORMAL400.py helpers with a stubbed module 09 (no CIME, no Slurm)."""
import importlib.util
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("m20", HERE / "20_needleleaf_rerun_AD400_NORMAL400.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


STREAMS = """<file id="stream" version="2.0"><stream_info name="CLMGSWP3v1.Solar"><datafiles>
<file>{f}</file></datafiles><year_first>2001</year_first></stream_info></file>"""


class T(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.squeue = ""
        self.env = {}
        R = types.SimpleNamespace(USER="u", SEG=5, fail=self._fail, digest=lambda p: Path(p).read_bytes().hex(),
                                  cmd=lambda argv, cwd=None, timeout=0: self.squeue,
                                  xq=lambda case, k: self.env[(Path(case).name, k)])
        self.m.R = R

    @staticmethod
    def _fail(s):
        raise RuntimeError(s)

    def test_jobs_exact_case_only(self):
        self.squeue = ("1|run.FI-Sod_B01_FIXNC_AD400|RUNNING\n2|st_archive.FI-Sod_B01_FIXNC_AD400|PENDING\n"
                       "3|run.FI-Sod_B01_FIXNC_AD400_NLF|RUNNING\n4|run.FI-Sod_B01_FIXNC_AD400_FIXF100|PENDING\n")
        self.assertEqual([r[0] for r in self.m.jobs("FI-Sod_B01_FIXNC_AD400")], ["1", "2"])
        self.assertEqual([r[0] for r in self.m.jobs("FI-Sod_B01_FIXNC_AD400_NLF")], ["3"])

    def test_settings_400_years(self):
        s = self.m.settings(Path("/o/X/run"), Path("/o/archive/X"))
        self.assertEqual((s["STOP_N"], s["RESUBMIT"], s["CONTINUE_RUN"]), ("5", "79", "FALSE"))

    def test_old_nc_files_only_case_output(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            run, arch, bld = d / "CASE" / "run", d / "archive" / "CASE", d / "CASE" / "bld"
            for p in (run, arch / "lnd" / "hist", arch / "rest" / "0401-01-01-00000", bld):
                p.mkdir(parents=True)
            keep = [run / "datm.streams.xml", run / "lnd_in", run / "cesm.log.1.gz", bld / "cesm.exe"]
            gone = [run / "CASE.clm2.r.0401-01-01-00000.nc", arch / "lnd" / "hist" / "CASE.clm2.h0.0001-01.nc",
                    arch / "rest" / "0401-01-01-00000" / "CASE.cpl.r.0401-01-01-00000.nc"]
            for p in keep + gone:
                p.write_text("x")
            self.env = {("CASE", "RUNDIR"): str(run), ("CASE", "DOUT_S_ROOT"): str(arch), ("CASE", "EXEROOT"): str(bld)}
            got = self.m.old_nc_files(d / "cases" / "CASE", "CASE")
            self.assertEqual(sorted(got), sorted(gone))
            self.env[("CASE", "RUNDIR")] = str(d / "shared" / "run")       # not the case's own: refuse
            with self.assertRaises(RuntimeError):
                self.m.old_nc_files(d / "cases" / "CASE", "CASE")

    def test_carry_streams(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            data = d / "forcing.nc"; data.write_text("x")
            (d / "new" / "CaseDocs").mkdir(parents=True); (d / "newrun").mkdir()
            eff = d / "eff.xml"; eff.write_text(STREAMS.format(f=data))
            doc = d / "new" / "CaseDocs" / "datm.streams.xml"
            doc.write_text("\n" + STREAMS.format(f=data) + "\n")          # same content, other whitespace
            self.assertIsNone(self.m.carry_streams(d / "new", d / "newrun", eff))
            doc.write_text(STREAMS.format(f=d / "other.nc"))                # regenerated file points elsewhere
            rec = self.m.carry_streams(d / "new", d / "newrun", eff)
            self.assertEqual(rec["data_files"], 1)
            self.assertEqual(doc.read_bytes(), eff.read_bytes())
            self.assertEqual((d / "newrun" / "datm.streams.xml").read_bytes(), eff.read_bytes())

    def test_site_list(self):
        self.assertEqual(len(self.m.SITES), 41)
        self.assertTrue(all(v.startswith(k) for k, v in self.m.SITES.items()))


if __name__ == "__main__":
    unittest.main()
