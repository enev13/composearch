from django.test import TestCase

from search.models import DistributorSourceModel
from search.search import get_active_distributors


class TestGetActiveDistributors(TestCase):
    def setUp(self) -> None:
        self.distributor = DistributorSourceModel.objects.create(
            name="TestShop",
            base_url="https://test.com/",
            search_string="search?q=%s",
            currency="EUR",
            included_vat=10,
            product_name_selector="#name",
            product_url_selector="a",
            product_picture_url_selector="img",
            product_price_selector="div > span",
            active=True,
        )
        self.distributor_0_vat = DistributorSourceModel.objects.create(
            name="TestShop",
            base_url="https://test.com/",
            search_string="search?q=%s",
            currency="EUR",
            included_vat=0,
            product_name_selector="#name",
            product_url_selector="a",
            product_picture_url_selector="img",
            product_price_selector="div > span",
            active=True,
        )

    async def test_get_distributors(self):
        self.assertEqual(
            await get_active_distributors(), [self.distributor, self.distributor_0_vat]
        )
