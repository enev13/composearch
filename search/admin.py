from django.contrib import admin

from search import models


class DistributorAdmin(admin.ModelAdmin):
    actions = ["activate", "deactivate"]

    def activate(self, request, queryset):
        queryset.update(active=True)

    def deactivate(self, request, queryset):
        queryset.update(active=False)


admin.site.register(models.DistributorSourceModel, DistributorAdmin)
