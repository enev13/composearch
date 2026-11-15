import json
import shutil
import tempfile
from io import BytesIO, StringIO, TextIOWrapper
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from search.models import DistributorSourceModel, DistributorStats

FIXTURE_LABEL = "test_sync_distributors"

TEST_FIXTURE = [
    {
        "model": "search.DistributorSourceModel",
        "fields": {
            "name": "TestShop",
            "base_url": "https://test.example/",
            "search_string": "search?query=%s",
            "currency": "EUR",
            "product_name_selector": "span.name",
            "product_url_selector": "a.url",
            "product_picture_url_selector": "img.pic",
            "product_price_selector": "span.price",
            "active": True,
            "included_vat": 20,
            "probe_query": "usb cable",
        },
    },
    {
        "model": "search.DistributorSourceModel",
        "fields": {
            "name": "NewShop",
            "base_url": "https://new.example/",
            "search_string": "search?q=%s",
            "currency": "BGN",
            "product_name_selector": ".n",
            "product_url_selector": ".u",
            "product_picture_url_selector": ".p",
            "product_price_selector": ".c",
            "active": False,
            "included_vat": 0,
            "probe_query": None,
        },
    },
]


def make_row(name: str, **overrides) -> DistributorSourceModel:
    fields = {
        "name": name,
        "base_url": "https://db.example/",
        "search_string": "search?db=%s",
        "currency": "USD",
        "product_name_selector": ".db-name",
        "product_url_selector": ".db-url",
        "product_picture_url_selector": ".db-pic",
        "product_price_selector": ".db-price",
        "active": True,
        "included_vat": 0,
        "probe_query": None,
    }
    fields.update(overrides)
    return DistributorSourceModel.objects.create(**fields)


class SyncDistributorsTests(TestCase):
    def setUp(self):
        super().setUp()
        self.fixture_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.fixture_dir, True)
        (self.fixture_dir / f"{FIXTURE_LABEL}.json").write_text(
            json.dumps(TEST_FIXTURE), encoding="utf-8"
        )
        override = override_settings(FIXTURE_DIRS=[str(self.fixture_dir)])
        override.enable()
        self.addCleanup(override.disable)

    def run_sync(self, *args) -> str:
        stdout = StringIO()
        self.stderr_output = StringIO()
        call_command(
            "sync_distributors", *args, stdout=stdout, stderr=self.stderr_output
        )
        return stdout.getvalue()

    def test_dry_run_changes_nothing(self):
        existing = make_row("TestShop", active=False)
        output = self.run_sync("--fixture", FIXTURE_LABEL)

        self.assertIn("DRY RUN", output)
        self.assertIn("1 to create", output)
        self.assertIn("1 to update", output)
        existing.refresh_from_db()
        self.assertEqual(existing.currency, "USD")
        self.assertFalse(existing.active)
        self.assertFalse(DistributorSourceModel.objects.filter(name="NewShop").exists())

    def test_apply_updates_fields_and_preserves_runtime_active(self):
        existing = make_row("TestShop", active=False)
        self.run_sync("--fixture", FIXTURE_LABEL, "--apply")

        existing.refresh_from_db()
        self.assertFalse(existing.active)  # fixture says True, DB state wins
        self.assertEqual(existing.base_url, "https://test.example/")
        self.assertEqual(existing.currency, "EUR")
        self.assertEqual(existing.included_vat, 20)
        self.assertEqual(existing.probe_query, "usb cable")
        new = DistributorSourceModel.objects.get(name="NewShop")
        self.assertFalse(new.active)  # created rows take the fixture's active value
        self.assertEqual(new.currency, "BGN")

    def test_orphan_kept_without_prune(self):
        ghost = make_row("GhostShop")
        output = self.run_sync("--fixture", FIXTURE_LABEL, "--apply")

        self.assertIn("orphan    GhostShop", output)
        ghost.refresh_from_db()
        self.assertTrue(ghost.active)

    def test_prune_deactivates_orphan_but_keeps_row_and_stats(self):
        ghost = make_row("GhostShop")
        stats = DistributorStats.objects.create(distributor=ghost, total_attempts=3)
        self.run_sync("--fixture", FIXTURE_LABEL, "--apply", "--prune")

        ghost.refresh_from_db()
        self.assertFalse(ghost.active)
        self.assertTrue(
            DistributorSourceModel.objects.filter(name="GhostShop").exists()
        )
        stats.refresh_from_db()
        self.assertEqual(stats.total_attempts, 3)

    def test_idempotent_second_run(self):
        self.run_sync("--fixture", FIXTURE_LABEL, "--apply")
        output = self.run_sync("--fixture", FIXTURE_LABEL, "--apply")

        self.assertIn("0 to create, 0 to update", output)
        self.assertIn("unchanged TestShop", output)
        self.assertIn("unchanged NewShop", output)
        self.assertEqual(DistributorSourceModel.objects.count(), 2)

    def test_duplicate_fixture_name_raises(self):
        duplicate = [TEST_FIXTURE[0], dict(TEST_FIXTURE[0])]
        (self.fixture_dir / "dup_distributors.json").write_text(
            json.dumps(duplicate), encoding="utf-8"
        )
        with self.assertRaises(CommandError):
            self.run_sync("--fixture", "dup_distributors", "--apply")

    def test_duplicate_database_names_sync_first_row_only(self):
        first = make_row("TestShop", probe_query="first")
        make_row("TestShop", probe_query="second")
        self.run_sync("--fixture", FIXTURE_LABEL, "--apply")

        first.refresh_from_db()
        self.assertEqual(first.probe_query, "usb cable")  # synced
        self.assertIn(
            "multiple database rows named 'TestShop'", self.stderr_output.getvalue()
        )
        self.assertEqual(
            DistributorSourceModel.objects.filter(name="TestShop").count(), 2
        )

    def test_missing_fixture_raises(self):
        with self.assertRaises(CommandError):
            self.run_sync("--fixture", "no_such_fixture", "--apply")

    def test_legacy_console_codepage_output_does_not_crash(self):
        # A cp1251 console cannot encode "ü"; the command must degrade it to
        # `?` instead of raising UnicodeEncodeError (e.g. Bürklin Elektronik).
        unicode_fixture = [
            {
                "model": "search.DistributorSourceModel",
                "fields": dict(TEST_FIXTURE[0]["fields"], name="Bürklin Elektronik"),
            }
        ]
        (self.fixture_dir / "unicode_distributors.json").write_text(
            json.dumps(unicode_fixture), encoding="utf-8"
        )
        raw = BytesIO()
        console = TextIOWrapper(raw, encoding="cp1251", errors="strict")

        with mock.patch("sys.stdout", console):
            call_command("sync_distributors", "--fixture", "unicode_distributors")
        console.flush()

        output = raw.getvalue().decode("cp1251")
        self.assertIn("create    B?rklin Elektronik", output)
        self.assertIn("DRY RUN", output)

    def test_real_fixture_applies_cleanly(self):
        real_fixture = (
            Path(DistributorSourceModel._meta.app_config.path)
            / "fixtures"
            / "distributors.json"
        )
        entries = [
            entry
            for entry in json.loads(real_fixture.read_text(encoding="utf-8"))
            if entry["model"] == "search.DistributorSourceModel"
        ]

        self.run_sync("--fixture", "distributors", "--apply")
        self.assertEqual(DistributorSourceModel.objects.count(), len(entries))

        output = self.run_sync("--fixture", "distributors", "--apply")
        self.assertIn("0 to create, 0 to update", output)
