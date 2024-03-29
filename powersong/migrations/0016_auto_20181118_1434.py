# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-11-18 14:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('powersong', '0015_auto_20181117_2317'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlaggedArtist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('artist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='powersong.Artist')),
                ('poweruser', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='powersong.PowerUser')),
            ],
        ),
        migrations.CreateModel(
            name='FlaggedSong',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('poweruser', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='powersong.PowerUser')),
                ('song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='powersong.Song')),
            ],
        ),
        migrations.AddField(
            model_name='effort',
            name='flagged',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='effort',
            name='flagged_hr',
            field=models.BooleanField(default=False),
        ),
    ]
