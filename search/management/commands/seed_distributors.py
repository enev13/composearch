from django.core.management import call_command
from django.core.management.base import BaseCommand

from search.models import DistributorSourceModel


class Command(BaseCommand):
    help = "Seeds distributor data from the fixture if none exists yet."

    def handle(self, *args, **options):
        if DistributorSourceModel.objects.exists():
            self.stdout.write("Distributor data already present; skipping seed.")
            return
        call_command("loaddata", "distributors.json")
        self.stdout.write("Distributor data seeded.")