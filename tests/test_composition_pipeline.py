import unittest
from datetime import datetime, timedelta, timezone

from app.composition import build_episode_preview
from app.rss_collection import CollectedItem, collect_fresh_items


class CompositionPipelineTests(unittest.TestCase):
    def test_weighted_allocation_prefers_higher_weight(self):
        now = datetime.now(timezone.utc)
        items_by_category = {
            "catA": [
                CollectedItem(
                    item_key=f"a{i}",
                    title=f"A{i}",
                    link=f"https://a/{i}",
                    published_at=now - timedelta(hours=1),
                    source_id="srcA",
                    source_title="Source A",
                    category_id="catA",
                    category_name="Categorie A",
                )
                for i in range(12)
            ],
            "catB": [
                CollectedItem(
                    item_key=f"b{i}",
                    title=f"B{i}",
                    link=f"https://b/{i}",
                    published_at=now - timedelta(hours=1),
                    source_id="srcB",
                    source_title="Source B",
                    category_id="catB",
                    category_name="Categorie B",
                )
                for i in range(12)
            ],
        }
        weights = {"catA": 70, "catB": 30}

        preview = build_episode_preview(items_by_category, weights, duration_target_minutes=10)
        used = preview["used_seconds_by_category"]
        self.assertGreaterEqual(used.get("catA", 0), used.get("catB", 0))

    def test_overflow_trimming_order_conclusion_then_transition(self):
        now = datetime.now(timezone.utc)
        items_by_category = {
            "catA": [
                CollectedItem(
                    item_key=f"a{i}",
                    title=f"A{i}",
                    link=f"https://a/{i}",
                    published_at=now - timedelta(hours=2),
                    source_id="srcA",
                    source_title="Source A",
                    category_id="catA",
                    category_name="Categorie A",
                )
                for i in range(20)
            ],
            "catB": [
                CollectedItem(
                    item_key=f"b{i}",
                    title=f"B{i}",
                    link=f"https://b/{i}",
                    published_at=now - timedelta(hours=2),
                    source_id="srcB",
                    source_title="Source B",
                    category_id="catB",
                    category_name="Categorie B",
                )
                for i in range(20)
            ],
        }
        preview = build_episode_preview(items_by_category, {"catA": 50, "catB": 50}, duration_target_minutes=1)
        trim_log = preview["sections"]["trim_log"]
        self.assertTrue(trim_log)
        self.assertEqual(trim_log[0], "conclusion")

    def test_freshness_filter_48h_excludes_stale_items(self):
        now = datetime.now(timezone.utc)
        bindings = [
            {
                "category_id": "catA",
                "category_name": "Categorie A",
                "default_weight": 1,
                "source_id": "srcA",
                "source_title": "Source A",
                "source_url": "https://example.com/feed",
            }
        ]

        import app.rss_collection as rss_collection

        original_fetch = rss_collection._fetch_source_items
        try:
            rss_collection._fetch_source_items = lambda _: [
                {"title": "fresh", "link": "https://fresh", "published_at": now - timedelta(hours=4)},
                {"title": "stale", "link": "https://stale", "published_at": now - timedelta(hours=96)},
            ]
            items = collect_fresh_items(bindings, max_age_hours=48)
        finally:
            rss_collection._fetch_source_items = original_fetch

        titles = [item.title for item in items["catA"]]
        self.assertIn("fresh", titles)
        self.assertNotIn("stale", titles)


if __name__ == "__main__":
    unittest.main()
