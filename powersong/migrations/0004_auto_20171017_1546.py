# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-10-17 15:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('powersong', '0003_auto_20171015_1757'),
    ]

    operations = [
        migrations.AddField(
            model_name='effort',
            name='diff_avg_watts',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='effort',
            name='diff_last_watts',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
