# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-02-07 00:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('powersong', '0006_auto_20171107_1512'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='total_ascent',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='activity',
            name='total_descent',
            field=models.FloatField(blank=True, null=True),
        ),
    ]