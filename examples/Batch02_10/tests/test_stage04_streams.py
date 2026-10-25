"""Regression fixtures for DATM XML selection; no HPC files or CIME execution."""
import contextlib
import importlib.util
import io
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "stage04", Path(__file__).resolve().parents[1] / "scripts/04_prepare_four_AD5_cases.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = {"site": "FI-Hyy", "stream_year_first": [1997],
                       "stream_year_last": [1998], "recorded_forcing_folders": [str(self.base)]}
        self.files = [self.base / ("FI-Hyy_DATM_" + str(y) + "_PROVISIONAL.nc") for y in (1997, 1998)]
        for p in self.files:
            p.write_bytes(b"fixture")
        self.xml = self.base / "datm.streams.xml"

    def tree(self, *, namespace=False, extra=False, root_stream=False):
        tag = lambda s: "{urn:datm-fixture}" + s if namespace else s
        root = ET.Element(tag("stream_info") if root_stream else tag("file"))
        tower = root if root_stream else ET.SubElement(root, tag("stream_info"))
        tower.set("name", "CLM_USRDAT.UNSET")
        for key, value in (("year_first", 1997), ("year_last", 1998), ("year_align", 1997)):
            ET.SubElement(tower, tag(key)).text = str(value)
        data = ET.SubElement(tower, tag("datafiles"))
        for p in self.files:
            ET.SubElement(data, tag("file")).text = str(p)
        if extra:
            aerosol = ET.SubElement(root, tag("stream_info"), {"name": "AEROSOL"})
            ET.SubElement(aerosol, tag("taxmode")).text = "cycle"
        return root, tower, data

    def check(self, root):
        ET.ElementTree(root).write(self.xml, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            return B.stream_check(self.xml, self.source)

    def test_root_namespaces_and_ancillary_streams(self):
        for ns, extra, root_stream in ((False, False, False), (True, False, False),
                                       (False, True, False), (True, True, False), (True, False, True)):
            with self.subTest(ns=ns, extra=extra, root_stream=root_stream):
                root, _, _ = self.tree(namespace=ns, extra=extra, root_stream=root_stream)
                self.check(root)

    def test_full_ancillary_signature_retained(self):
        root, _, _ = self.tree(extra=True)
        before = self.check(root)
        root.find("./stream_info[@name='AEROSOL']/taxmode").text = "extend"
        self.assertNotEqual(before, self.check(root))

    def test_missing_or_duplicate_named_tower_rejected(self):
        root, tower, _ = self.tree(extra=True)
        tower.set("name", "OTHER_TOWER")
        with self.assertRaisesRegex(RuntimeError, "stream_names"):
            self.check(root)
        tower.set("name", "CLM_USRDAT.UNSET")
        ET.SubElement(root, "stream_info", {"name": "CLM_USRDAT.UNSET"})
        with self.assertRaisesRegex(RuntimeError, "matches=2"):
            self.check(root)

    def test_wrong_year_rejected(self):
        root, tower, _ = self.tree()
        tower.find("year_align").text = "1998"
        with self.assertRaisesRegex(RuntimeError, "year mismatch"):
            self.check(root)

    def test_wrong_order_rejected(self):
        root, _, data = self.tree()
        data[0].text, data[1].text = data[1].text, data[0].text
        with self.assertRaisesRegex(RuntimeError, "filename/order"):
            self.check(root)

    def test_wrong_site_and_unknown_suffix_rejected(self):
        for value in ("IT-MBo_DATM_1997_PROVISIONAL.nc", "FI-Hyy_DATM_1997_OTHER.nc"):
            root, _, data = self.tree()
            data[0].text = str(self.base / value)
            with self.assertRaisesRegex(RuntimeError, "filename/order"):
                self.check(root)

    def test_wrong_folder_and_missing_file_rejected(self):
        root, _, data = self.tree()
        data[0].text = str(self.base / "wrong" / self.files[0].name)
        with self.assertRaisesRegex(RuntimeError, "missing/changed folder"):
            self.check(root)
        root, _, _ = self.tree()
        self.files[0].unlink()
        with self.assertRaisesRegex(RuntimeError, "missing/changed folder"):
            self.check(root)

    def test_plain_filenames_remain_supported(self):
        self.source["site"] = "CH-Fru"
        for i, y in enumerate((1997, 1998)):
            self.files[i] = self.base / ("CH-Fru_DATM_" + str(y) + ".nc")
            self.files[i].write_bytes(b"fixture")
        root, _, _ = self.tree()
        self.check(root)

    def test_arbitrary_provisional_suffix_not_accepted_for_other_sites(self):
        self.source["site"] = "CH-Fru"
        self.files = [self.base / ("CH-Fru_DATM_" + str(y) + "_PROVISIONAL.nc") for y in (1997, 1998)]
        root, _, _ = self.tree()
        with self.assertRaisesRegex(RuntimeError, "filename/order"):
            self.check(root)


if __name__ == "__main__":
    unittest.main()
