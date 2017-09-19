# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-09-16 18:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0006_auto_20170916_1230'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='img_xl',
            field=models.ImageField(blank=True, height_field='xl_height', null=True, upload_to='blogs_images', width_field='xl_width'),
        ),
        migrations.AddField(
            model_name='image',
            name='xl_height',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='image',
            name='xl_width',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]