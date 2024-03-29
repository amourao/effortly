# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-11-15 14:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('powersong', '0012_effort_time'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='songeffortperuser',
            name='song',
        ),
        migrations.RemoveField(
            model_name='songeffortperuser',
            name='user',
        ),
        migrations.AddField(
            model_name='effort',
            name='hr',
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='song',
            name='album_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='song',
            name='spotify_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.DeleteModel(
            name='SongEffortPerUser',
        ),
    ]
