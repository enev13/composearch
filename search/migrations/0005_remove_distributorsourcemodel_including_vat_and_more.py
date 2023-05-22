# Generated by Django 4.1.9 on 2023-05-22 09:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0004_distributorsourcemodel_active"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="distributorsourcemodel",
            name="including_vat",
        ),
        migrations.AddField(
            model_name="distributorsourcemodel",
            name="included_vat",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
