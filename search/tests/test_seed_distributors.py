from django.core.management import call_command
from django.test import TestCase

from search.models import DistributorSourceModel


class TestSeedDistributors(TestCase):
    def test_seeds_when_empty(self):
        call_command("seed_distributors")
        self.assertGreater(DistributorSourceModel.objects.count(), 0)

    def test_is_idempotent(self):
        call_command("seed_distributors")
        count_after_first = DistributorSourceModel.objects.count()

        call_command("seed_distributors")
        self.assertEqual(
            DistributorSourceModel.objects.count(), count_after_first
        )

    def test_skips_when_distributors_exist(self):
        DistributorSourceModel.objects.create(
            name="TestShop",
            base_url="https://test.com/",
            search_string="search?q=%s",
            currency="EUR",
            included_vat=19,
            product_name_selector="#name",
            product_url_selector="a",
            product_picture_url_selector="img",
            product_price_selector="div > span",
            active=True,
        )

        call_command("seed_distributors")

        self.assertEqual(DistributorSourceModel.objects.count(), 1)