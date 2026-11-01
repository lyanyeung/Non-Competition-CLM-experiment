import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('temperature_proposals', HERE / '31_propose_six_temperature_repairs.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def point(t, v, era, q='0'):
    return {'tower': {'TA_F': str(t), 'TA_F_QC': q, 'VPD_F': str(v), 'VPD_F_QC': q},
            'selected': {'TA_USE': str(t), 'VPD_USE': str(v), 'PSRF': '94200'},
            'era': {'TA_ERA': str(era)}}


class ProposalTests(unittest.TestCase):
    def test_us_bar_block_is_proposed_only_not_applied(self):
        frames = {'2015-11-06 19:30:00': point(19.706, 9.919, 17.701),
                  '2015-11-06 20:00:00': point(-20.171, .617, 17.726),
                  '2015-11-06 20:30:00': point(8.508, 5.194, 17.554),
                  '2015-11-06 21:00:00': point(-17.178, .82, 17.381),
                  '2015-11-06 21:30:00': point(17.455, 9.392, 17.190)}
        block, status = mod.propose('2015-11-06 20:00:00', frames)
        self.assertEqual(status, 'PROVISIONAL_SHORT_BLOCK_CANDIDATE_NOT_APPLIED')
        self.assertEqual(len(block), 3)
        self.assertAlmostEqual(block[0]['proposed_TA_C'], 19.14325)
        self.assertAlmostEqual(block[1]['proposed_TA_C'], 18.5805)
        self.assertEqual(frames['2015-11-06 20:00:00']['tower']['TA_F'], '-20.171')
        self.assertTrue(all(0 < x['proposed_QBOT_kgkg'] < .08 for x in block))

    def test_qc1_intervening_point_prevents_automatic_candidate(self):
        frames = {'2015-11-06 19:30:00': point(19.706, 9.919, 17.701),
                  '2015-11-06 20:00:00': point(-20.171, .617, 17.726),
                  '2015-11-06 20:30:00': point(8.508, 5.194, 17.554, '1'),
                  '2015-11-06 21:00:00': point(-17.178, .82, 17.381),
                  '2015-11-06 21:30:00': point(17.455, 9.392, 17.190)}
        block, status = mod.propose('2015-11-06 20:00:00', frames)
        self.assertIsNone(block)
        self.assertEqual(status, 'HOLD_INTERIOR_NOT_OBSERVED_QC0_OR_ALREADY_CHANGED')

    def test_humidity_closure_and_rejects_supersaturation_candidate(self):
        q = mod.humidity(19., 9., 94200.)
        es = 6.112 * __import__('math').exp(17.67*19/(19+243.5))
        e = q*(94200/100)/(.622 + .378*q)
        self.assertAlmostEqual(es-e, 9.)
        with self.assertRaises(ValueError): mod.humidity(19., -1., 94200.)

    def test_deduplicates_qc0_endpoint_from_adjacent_edges(self):
        with tempfile.TemporaryDirectory(dir=HERE) as d:
            path = Path(d) / 'events.csv'
            columns = ['left_time_local','right_time_local','tower_left_TA_QC','tower_right_TA_QC',
                       'tower_left_C','tower_right_C','era_left_C','era_right_C',
                       'left_selected_differs_tower','right_selected_differs_tower']
            rows = [{'left_time_local':'2015-11-06 19:30:00','right_time_local':'2015-11-06 20:00:00',
                     'tower_left_TA_QC':'0','tower_right_TA_QC':'0','tower_left_C':'19.7','tower_right_C':'-20.1',
                     'era_left_C':'17.7','era_right_C':'17.7','left_selected_differs_tower':'False','right_selected_differs_tower':'False'},
                    {'left_time_local':'2015-11-06 20:00:00','right_time_local':'2015-11-06 20:30:00',
                     'tower_left_TA_QC':'0','tower_right_TA_QC':'0','tower_left_C':'-20.1','tower_right_C':'8.5',
                     'era_left_C':'17.7','era_right_C':'17.5','left_selected_differs_tower':'False','right_selected_differs_tower':'False'}]
            with path.open('w', newline='') as f:
                w=csv.DictWriter(f, fieldnames=columns); w.writeheader(); w.writerows(rows)
            result = mod.read_candidates(path)
            self.assertEqual(list(result), ['2015-11-06 20:00:00'])
            self.assertEqual(result['2015-11-06 20:00:00']['jump_count'], 2)


if __name__ == '__main__': unittest.main()

