# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-11-04 12:13
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0019_auto_20171104_0742'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='blogimage',
            name='portrait',
        ),
    ]
