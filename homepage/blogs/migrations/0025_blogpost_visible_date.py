# Generated by Django 2.0.5 on 2018-05-28 06:34

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0024_remove_blogpost_published'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='visible_date',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2018, 5, 28, 6, 34, 34, 632115, tzinfo=utc)),
        ),
    ]