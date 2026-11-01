import csv
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


registry = load('registry88_test', '26_site_registry.py')
driver = load('driver88_test', '27_plot_sites_88.py')
publisher = load('publisher88_test', '28_publish_sites_88.py')


class InventoryTests(unittest.TestCase):
    def test_registry_matches_historical_icos_manifest(self):
        rows = registry.records()
        self.assertEqual(Counter(r['network'] for r in rows), {'ICOS': 38, 'AmeriFlux': 50})
        self.assertEqual(Counter(r['batch'] for r in rows if r['network'] == 'ICOS'),
                         {'Batch01': 10, 'Batch02': 10, 'Batch03': 10, 'Example': 2, 'Unassigned': 6})
        source = HERE.parents[1] / 'repository/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261025.csv'
        if source.exists():
            with source.open(encoding='utf-8-sig', newline='') as f:
                actual = {r['site']: r['fixnc_cohort'] for r in csv.DictReader(f)}
            normalize = {'Example (legacy)': 'Example', 'Not assigned': 'Unassigned'}
            actual = {k: normalize.get(v, v) for k, v in actual.items()}
            self.assertEqual({r['site']: r['batch'] for r in rows if r['network'] == 'ICOS'}, actual)

    def test_only_referenced_completed_same_site_pair_is_plotted(self):
        sample = [
            {'name': 'DE-Hai_AD', 'site': 'DE-Hai', 'mode': 'AD', 'verdict': 'DONE'},
            {'name': 'DE-Hai_N', 'site': 'DE-Hai', 'mode': 'NORMAL', 'verdict': 'DONE', 'refcase': 'DE-Hai_AD'},
            {'name': 'DE-Hai_N2', 'site': 'DE-Hai', 'mode': 'NORMAL', 'verdict': 'RUNNING', 'refcase': 'DE-Hai_AD'},
            {'name': 'US-Me2_N', 'site': 'US-Me2', 'mode': 'NORMAL', 'verdict': 'DONE', 'refcase': 'DE-Hai_AD'},
            {'name': 'US-UiD_AD', 'site': 'US-UiD', 'mode': 'AD', 'verdict': 'RUNNING'},
        ]
        scan = SimpleNamespace(USER='user', OUT=Path('/model'), BASE=Path('/model'), scan=lambda *a: sample)
        common = SimpleNamespace(verified_queue=lambda _: {}, restart_check=lambda *a: None,
                                 stream_status=lambda *a: ('MATCH', 'same', 'same'))
        calls, snapshots = [], {}
        def process(pair, args):
            calls.append(pair)
            folder = args.output_root / pair['site'] / pair['normal']
            folder.mkdir(parents=True)
            for suffix in driver.SUFFIXES:
                (folder / (pair['site'] + suffix)).write_bytes(b'png')
            return {'Status': 'OK'}
        modules = {'site_registry': registry, 'progress_scan': scan, 'all_sites': common,
                   'plot_stage15': SimpleNamespace(process=process)}
        def save(path, rows, required): snapshots[path.name] = [dict(r) for r in rows]
        with tempfile.TemporaryDirectory(dir=HERE) as tmp, patch.object(driver, 'load', side_effect=lambda n, p: modules[n]), \
             patch.object(driver, 'write_csv', side_effect=save), \
             patch.object(sys, 'argv', ['driver', '--output-root', str(Path(tmp) / 'out')]):
            self.assertEqual(driver.main(), 1)
        self.assertEqual([(p['site'], p['ad'], p['normal']) for p in calls], [('DE-Hai', 'DE-Hai_AD', 'DE-Hai_N')])
        sites = {r['Site']: r for r in snapshots['site_status.csv']}
        self.assertEqual(len(sites), 88)
        self.assertEqual(sites['DE-Hai']['Status'], 'COMPLETE')
        self.assertEqual(sites['US-Me2']['Status'], 'NOT_READY_OR_ERROR')
        self.assertEqual(sites['US-UiD']['Status'], 'RUNNING')
        self.assertEqual(sites['US-UiD']['Batch'], 'Batch05')

    def test_publisher_exports_only_figures_and_sanitized_provenance(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            base = Path(tmp); root = base / 'out'; tool = base / 'tools'
            root.mkdir(); tool.mkdir()
            shutil.copyfile(HERE / '26_site_registry.py', tool / 'registry.py')
            for name in publisher.SOURCES:
                if name != 'registry.py': (tool / name).write_text(name)
            digests = {name: hashlib.sha256((tool / name).read_bytes()).hexdigest() for name in publisher.SOURCES}
            rid = 'login-' + 'a' * 32; sha = 'b' * 40
            (root / 'RUN_COMPLETE.json').write_text(json.dumps({'run_id': rid, 'source_commit': sha,
                                                                'exit_code': 1, 'code_sha256': digests}))
            sites = [{'Site': r['site'], 'Network': r['network'], 'Batch': r['batch'],
                      'Status': 'COMPLETE' if r['site'] == 'DE-Hai' else 'NO_NORMAL_CASE'} for r in registry.records()]
            cases = [{'Site': r['Site'], 'Normal_case': 'N' if r['Site'] == 'DE-Hai' else '',
                      'Status': 'OK' if r['Site'] == 'DE-Hai' else 'NO_NORMAL_CASE',
                      'Figures': 4 if r['Site'] == 'DE-Hai' else 0} for r in sites]
            for name, rows in [('site_status.csv', sites), ('case_status.csv', cases)]:
                with (root / name).open('w', newline='', encoding='utf-8') as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
            folder = root / 'DE-Hai' / 'N'; folder.mkdir(parents=True)
            for suffix in publisher.FIGURES:
                (folder / ('DE-Hai' + suffix)).write_bytes(b'\x89PNG\r\n\x1a\nFAKE')
            (folder / 'DE-Hai_metadata.json').write_text(json.dumps({'site': 'DE-Hai', 'ec_sources': [
                {'path': '/private/location/tower.csv', 'gpp_column': 'GPP_NT_VUT_REF'}]}))
            (folder / 'private_raw.csv').write_text('secret')
            observed = {}
            def git(*args, cwd=None, binary=False):
                if args[0] == 'clone': Path(args[-1]).mkdir(); return ''
                if args[0] == 'show':
                    path = args[1].split(':', 1)[1]
                    name = next(n for n, p in publisher.SOURCES.items() if p == path)
                    return (tool / name).read_bytes()
                if args[0] == 'rev-parse': return 'fakecommit'
                if args[0] == 'push':
                    target = next((Path(cwd) / 'figures/AD400_NORMAL400').iterdir())
                    observed['readme'] = (target / 'README.md').read_text()
                    observed['files'] = [p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()]
                    observed['provenance'] = next(target.rglob('*_provenance.json')).read_text()
                return ''
            with patch.object(publisher, 'command', side_effect=git), patch.object(sys, 'argv',
                 ['publisher', '--run', str(root), '--run-id', rid, '--tool', str(tool)]):
                publisher.main()
            self.assertEqual(len([x for x in observed['files'] if x.endswith('.png')]), 4)
            self.assertNotIn('private_raw.csv', ' '.join(observed['files']))
            self.assertNotIn('/private/location', observed['provenance'])
            self.assertIn('tower.csv', observed['provenance'])
            self.assertIn('US-UiD', observed['readme'])
            self.assertIn('unassigned sites', observed['readme'])


if __name__ == '__main__': unittest.main()

