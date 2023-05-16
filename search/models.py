from django.db import models


class DistributorSourceModel(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    base_url = models.URLField(max_length=256, null=False, blank=False)
    search_string = models.CharField(max_length=1024, null=False, blank=False)
    currency = models.CharField(max_length=3, null=False, blank=False)
    including_vat = models.BooleanField(default=True)
    product_name_selector = models.CharField(max_length=1024, null=False, blank=False)
    product_url_selector = models.CharField(max_length=1024, null=False, blank=False)
    product_picture_url_selector = models.CharField(max_length=1024, null=False, blank=False)
    product_price_selector = models.CharField(max_length=1024, null=False, blank=False)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.base_url}){' - INACTIVE' if not self.active else ''}"
