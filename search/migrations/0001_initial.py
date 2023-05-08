# Generated by Django 4.2.1 on 2023-05-05 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DistributorSourceModel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("base_url", models.URLField(max_length=256)),
                ("search_string", models.CharField(max_length=1024)),
                ("product_name_selector", models.CharField(max_length=256)),
                ("product_url_selector", models.CharField(max_length=1024)),
                ("product_picture_url_selector", models.CharField(max_length=256)),
                ("product_price_selector", models.CharField(max_length=256)),
            ],
        ),
    ]
