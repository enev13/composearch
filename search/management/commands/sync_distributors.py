"""Sync the distributor list from the fixture into the database.

The fixture (search/fixtures/distributors.json) is the canonical, git-versioned
definition of the distributor list; the database owns the runtime state (the
`active` flag, stats). Unlike a bare `loaddata`, this command upserts by name
(the fixture carries no primary keys), never duplicates rows, and never
touches `active` on existing rows — that flag belongs to the monitor and
admin actions.
"""

import io
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from search.models import DistributorSourceModel

MODEL_LABEL = "search.DistributorSourceModel"

# Fixture-driven definition fields. `name` is the match key and `active` is
# runtime state — neither is updated on existing rows.
DEFINITION_FIELDS = (
    "base_url",
    "search_string",
    "currency",
    "included_vat",
    "product_name_selector",
    "product_url_selector",
    "product_picture_url_selector",
    "product_price_selector",
    "probe_query",
)


def find_fixture_file(label: str) -> Path:
    """Locate `<label>.json` in FIXTURE_DIRS, then app fixtures directories."""
    fixture_dirs = [
        Path(directory) for directory in getattr(settings, "FIXTURE_DIRS", [])
    ]
    fixture_dirs += [
        Path(app_config.path) / "fixtures"
        for app_config in django_apps.get_app_configs()
    ]
    for directory in fixture_dirs:
        for candidate in (directory / label, directory / f"{label}.json"):
            if candidate.is_file():
                return candidate
    raise CommandError(
        f"Fixture '{label}' not found in FIXTURE_DIRS or app fixtures directories."
    )


def load_fixture(label: str) -> tuple[Path, list[DistributorSourceModel]]:
    """Deserialize the fixture and return (path, unsaved model instances)."""
    path = find_fixture_file(label)
    with open(path, encoding="utf-8") as file:
        raw = file.read()
    instances: dict[str, DistributorSourceModel] = {}
    for deserialized in serializers.deserialize("json", raw, ignorenonexistent=True):
        instance = deserialized.object
        if instance._meta.label != MODEL_LABEL:
            continue
        if instance.name in instances:
            raise CommandError(
                f"Duplicate distributor name '{instance.name}' in {path}."
            )
        instances[instance.name] = instance
    return path, list(instances.values())


class Command(BaseCommand):
    help = (
        "Sync DistributorSourceModel rows from the distributors fixture by name "
        "(upsert; preserves `active` and stats on existing rows). Dry run by default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="distributors",
            help="Fixture label (default: distributors).",
        )
        parser.add_argument(
            "--apply", action="store_true", help="Apply changes (default is a dry run)."
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Also deactivate database distributors missing from the fixture (never deletes).",
        )

    def handle(self, *args, **options):
        # Windows consoles with legacy codepages (e.g. cp1251) cannot encode
        # names like "Bürklin Elektronik"; degrade to `?` instead of crashing.
        for wrapper in (self.stdout, self.stderr):
            stream = getattr(wrapper, "_out", wrapper)
            if isinstance(stream, io.TextIOWrapper):
                stream.reconfigure(errors="replace")
        apply_changes = options["apply"]
        prune = options["prune"]
        path, entries = load_fixture(options["fixture"])

        rows_by_name: dict[str, DistributorSourceModel] = {}
        for row in DistributorSourceModel.objects.order_by("pk"):
            if row.name in rows_by_name:
                self.stderr.write(
                    f"Warning: multiple database rows named '{row.name}'; syncing the first one only."
                )
                continue
            rows_by_name[row.name] = row

        creates: list[DistributorSourceModel] = []
        updates: list[
            tuple[DistributorSourceModel, DistributorSourceModel, list[str]]
        ] = []
        unchanged: list[str] = []
        fixture_names: set[str] = set()
        for entry in entries:
            fixture_names.add(entry.name)
            row = rows_by_name.get(entry.name)
            if row is None:
                creates.append(entry)
                continue
            changed_fields = [
                field
                for field in DEFINITION_FIELDS
                if getattr(entry, field) != getattr(row, field)
            ]
            if changed_fields:
                updates.append((row, entry, changed_fields))
            else:
                unchanged.append(entry.name)
        orphans = [
            row for name, row in rows_by_name.items() if name not in fixture_names
        ]

        self.stdout.write(
            f"Loaded {len(entries)} distributor definition(s) from {path}"
        )
        for entry in creates:
            self.stdout.write(self.style.MIGRATE_LABEL(f"create    {entry.name}"))
        for row, entry, changed_fields in updates:
            self.stdout.write(
                self.style.MIGRATE_LABEL(
                    f"update    {entry.name} ({', '.join(changed_fields)})"
                )
            )
        for name in unchanged:
            self.stdout.write(f"unchanged {name}")
        for row in orphans:
            note = (
                "deactivate (--prune)"
                if prune and row.active
                else ("kept" if row.active else "already inactive")
            )
            self.stdout.write(self.style.WARNING(f"orphan    {row.name} — {note}"))

        summary = (
            f"Summary: {len(creates)} to create, {len(updates)} to update, "
            f"{len(unchanged)} unchanged, {len(orphans)} orphan(s)."
        )
        self.stdout.write(self.style.SUCCESS(summary))

        if not apply_changes:
            self.stdout.write("DRY RUN — pass --apply to write changes.")
            return

        with transaction.atomic():
            for entry in creates:
                fields = {
                    field.attname: getattr(entry, field.attname)
                    for field in DistributorSourceModel._meta.concrete_fields
                    if field.attname != "id"
                }
                DistributorSourceModel.objects.create(**fields)
            for row, entry, changed_fields in updates:
                for field in changed_fields:
                    setattr(row, field, getattr(entry, field))
                row.save(update_fields=changed_fields)
            if prune:
                for row in orphans:
                    if row.active:
                        row.active = False
                        row.save(update_fields=["active"])
        self.stdout.write(self.style.SUCCESS("Applied."))
