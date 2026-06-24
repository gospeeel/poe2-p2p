import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from poe2_p2p.alerts import filter_profit_alerts
from poe2_p2p.app import build_sample_opportunities
from poe2_p2p.calibration import load_region, save_region
from poe2_p2p.calculator import ArbitrageCalculator
from poe2_p2p.candidates import parse_poe_ninja_currency_rows, shortlist_candidates
from poe2_p2p.config import CropRegion
from poe2_p2p.dashboard import export_history_dashboard
from poe2_p2p.exporter import export_opportunities_csv
from poe2_p2p.models import RateEdge
from poe2_p2p.parser import normalize_ratio_to_edges, parse_ratio
from poe2_p2p.ranking import rank_opportunities
from poe2_p2p.sample_data import EXALTED
from poe2_p2p.storage import SQLiteStore
from poe2_p2p.validation import validate_ratio_range


class ParserTest(unittest.TestCase):
    def test_parse_ratio(self):
        self.assertEqual(parse_ratio("1 : 2050"), (1.0, 2050.0))
        self.assertEqual(parse_ratio("6,34 : 1"), (6.34, 1.0))

    def test_normalize_ratio_to_edges(self):
        edges = normalize_ratio_to_edges(
            "Omen of Whittling",
            "Exalted Orb",
            "1 : 2050",
            "test",
            0.99,
        )
        self.assertEqual(edges[0].from_currency, "Omen of Whittling")
        self.assertEqual(edges[0].to_currency, "Exalted Orb")
        self.assertEqual(edges[0].rate, 2050.0)
        self.assertAlmostEqual(edges[1].rate, 1 / 2050)


class CalculatorTest(unittest.TestCase):
    def test_sample_opportunity_matches_screenshot_math(self):
        _, opportunities = build_sample_opportunities()
        profitable = [item for item in opportunities if item.net_profit > 0]

        self.assertEqual(len(profitable), 1)
        opportunity = profitable[0]
        self.assertEqual(opportunity.input_currency, EXALTED)
        self.assertAlmostEqual(opportunity.output_amount, 2231.68)
        self.assertAlmostEqual(opportunity.net_profit, 181.68)
        self.assertAlmostEqual(opportunity.roi_percent, 8.862439, places=5)

    def test_profit_adjustments_and_profit_per_hour(self):
        _, opportunities = build_sample_opportunities(
            slippage_buffer_percent=10,
            spread_loss_percent=10,
            rounding_loss_flat=1,
            gold_cost_flat=2,
            cycles_per_hour=3,
        )
        opportunity = [item for item in opportunities if item.net_profit > 0][0]
        self.assertAlmostEqual(opportunity.net_profit, 142.344)
        self.assertAlmostEqual(opportunity.profit_per_hour, 427.032)
        self.assertGreater(opportunity.score, 0)

    def test_multi_hop_cycle_search(self):
        rates = [
            RateEdge("A", "B", 2.0, "test"),
            RateEdge("B", "C", 2.0, "test"),
            RateEdge("C", "D", 2.0, "test"),
            RateEdge("D", "A", 0.2, "test"),
        ]
        opportunities = ArbitrageCalculator(rates).find_cycles("A", 10, max_hops=4)
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0].path, ("A", "B", "C", "D", "A"))
        self.assertAlmostEqual(opportunities[0].net_profit, 6.0)


class UtilityTest(unittest.TestCase):
    def test_export_alerts_calibration_storage_and_candidates(self):
        _, opportunities = build_sample_opportunities()
        profitable = [item for item in opportunities if item.net_profit > 0]

        with TemporaryDirectory() as directory:
            root = Path(directory)

            calibration_path = root / "calibration.json"
            region = CropRegion.from_csv("385,122,90,18")
            save_region(calibration_path, region)
            self.assertEqual(load_region(calibration_path), region)

            csv_path = root / "opportunities.csv"
            export_opportunities_csv(profitable, csv_path)
            csv_text = csv_path.read_text(encoding="utf-8")
            self.assertIn("net_profit", csv_text)
            self.assertIn("Exalted Orb -> Omen", csv_text)

            alerts = filter_profit_alerts(profitable, min_net_profit=100, min_roi_percent=2)
            self.assertEqual(alerts, profitable)

            db_path = root / "rates.db"
            store = SQLiteStore(db_path)
            store.init_schema()
            store.save_opportunities(profitable)
            recent = store.list_recent_opportunities(1)
            self.assertEqual(len(recent), 1)
            self.assertAlmostEqual(store.total_recorded_net_profit(), 181.68)

            dashboard_path = root / "history.html"
            export_history_dashboard(recent, dashboard_path)
            dashboard_text = dashboard_path.read_text(encoding="utf-8")
            self.assertIn("POE2 P2P History", dashboard_text)
            self.assertIn("Exalted Orb", dashboard_text)

            payload = {
                "lines": [
                    {"currencyTypeName": "A", "chaosEquivalent": 10, "count": 5, "details": {"change": 10}},
                    {"currencyTypeName": "B", "chaosEquivalent": 1, "count": 100, "details": {"change": 0}},
                    {"currencyTypeName": "C", "chaosEquivalent": 50, "count": 1, "details": {"change": -5}},
                ]
            }
            candidates = parse_poe_ninja_currency_rows(payload)
            shortlist = shortlist_candidates(candidates, limit=2)
            self.assertEqual([candidate.name for candidate in shortlist], ["B", "A"])

            new_payload = {
                "core": {"items": [{"id": "divine", "name": "Divine Orb"}]},
                "lines": [
                    {
                        "id": "divine",
                        "primaryValue": 1.0,
                        "volumePrimaryValue": 123.0,
                        "sparkline": {"totalChange": 5.0},
                    }
                ],
            }
            parsed = parse_poe_ninja_currency_rows(new_payload)
            self.assertEqual(parsed[0].name, "Divine Orb")
            self.assertEqual(parsed[0].volume_per_hour, 123.0)

    def test_ranking_and_ratio_validation(self):
        _, opportunities = build_sample_opportunities(cycles_per_hour=4)
        ranked = rank_opportunities(opportunities, key="profit_per_hour")
        self.assertGreater(ranked[0].profit_per_hour, 0)

        ok = validate_ratio_range(observed_rate=2050, expected_rate=2000, tolerance_percent=5)
        self.assertTrue(ok.ok)

        failed = validate_ratio_range(observed_rate=2050, expected_rate=1000, tolerance_percent=5)
        self.assertFalse(failed.ok)


class ConfigTest(unittest.TestCase):
    def test_crop_region_from_csv(self):
        region = CropRegion.from_csv("385,122,90,18")
        self.assertEqual(region.as_box(), (385, 122, 475, 140))
        self.assertEqual(
            region.as_mss(),
            {"left": 385, "top": 122, "width": 90, "height": 18},
        )

    def test_crop_region_rejects_invalid_size(self):
        with self.assertRaises(ValueError):
            CropRegion.from_csv("1,2,0,4")


if __name__ == "__main__":
    unittest.main()
