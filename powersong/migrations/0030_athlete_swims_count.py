# Generated by Django 4.1 on 2024-10-15 11:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('powersong', '0029_alter_activity_flagged_alter_activity_flagged_hr_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='athlete',
            name='swims_count',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]