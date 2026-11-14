from typing import ClassVar

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from search import models


class DistributorAdmin(admin.ModelAdmin):
    actions: ClassVar[list[str]] = ["activate", "deactivate"]

    def activate(self, request: HttpRequest, queryset: QuerySet[models.DistributorSourceModel]) -> None:
        queryset.update(active=True)

    def deactivate(self, request: HttpRequest, queryset: QuerySet[models.DistributorSourceModel]) -> None:
        queryset.update(active=False)


admin.site.register(models.DistributorSourceModel, DistributorAdmin)
