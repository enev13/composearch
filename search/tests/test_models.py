from django.test import TestCase
from search.models import DistributorSourceModel


class TestModels(TestCase):
    def setUp(self) -> None:
        self.distributor = DistributorSourceModel.objects.create(
            name="TestShop",
            base_url="https://test.com",
            search_string="search?q=%s",
            currency="EUR",
            including_vat=True,
            product_name_selector="#name",
            product_url_selector="#url",
            product_picture_url_selector="#picture",
            product_price_selector="#price",
            active=True,
        )

    def test_distributor_is_created(self):
        self.assertEqual(self.distributor.name, "TestShop")
        self.assertEqual(self.distributor.base_url, "https://test.com")
        self.assertEqual(self.distributor.search_string, "search?q=%s")
        self.assertEqual(self.distributor.currency, "EUR")
        self.assertEqual(self.distributor.including_vat, True)
        self.assertEqual(self.distributor.product_name_selector, "#name")
        self.assertEqual(self.distributor.product_url_selector, "#url")
        self.assertEqual(self.distributor.product_picture_url_selector, "#picture")
        self.assertEqual(self.distributor.product_price_selector, "#price")
        self.assertEqual(self.distributor.active, True)
        self.assertEqual(str(self.distributor), "TestShop (https://test.com)")

    def test_distributor_is_updated(self):
        self.distributor.name = "TestShop2"
        self.distributor.base_url = "https://test2.com"
        self.distributor.search_string = "search2?q=%s"
        self.distributor.currency = "USD"
        self.distributor.including_vat = False
        self.distributor.product_name_selector = "#name2"
        self.distributor.product_url_selector = "#url2"
        self.distributor.product_picture_url_selector = "#picture2"
        self.distributor.product_price_selector = "#price2"
        self.distributor.active = False
        self.assertEqual(self.distributor.name, "TestShop2")
        self.assertEqual(self.distributor.base_url, "https://test2.com")
        self.assertEqual(self.distributor.search_string, "search2?q=%s")
        self.assertEqual(self.distributor.currency, "USD")
        self.assertEqual(self.distributor.including_vat, False)
        self.assertEqual(self.distributor.product_name_selector, "#name2")
        self.assertEqual(self.distributor.product_url_selector, "#url2")
        self.assertEqual(self.distributor.product_picture_url_selector, "#picture2")
        self.assertEqual(self.distributor.product_price_selector, "#price2")
        self.assertEqual(self.distributor.active, False)
        self.assertEqual(str(self.distributor), "TestShop2 (https://test2.com) - INACTIVE")

    def test_distributor_is_deleted(self):
        self.distributor.delete()
        self.assertEqual(DistributorSourceModel.objects.count(), 0)

    def test_distributor_is_inactive(self):
        self.distributor.active = False
        self.assertEqual(str(self.distributor), "TestShop (https://test.com) - INACTIVE")

    def test_distributor_is_active(self):
        self.distributor.active = True
        self.assertEqual(str(self.distributor), "TestShop (https://test.com)")
