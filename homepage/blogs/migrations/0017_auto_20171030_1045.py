# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-10-30 10:45
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0016_auto_20171027_1916'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='blogmedia',
            name='blogpost',
        ),
        migrations.RemoveField(
            model_name='blogmedia',
            name='content_type',
        ),
        migrations.DeleteModel(
            name='BlogMedia',
        ),
    ]