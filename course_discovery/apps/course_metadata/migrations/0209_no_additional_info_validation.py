# -*- coding: utf-8 -*-
# Generated by Django 1.11.25 on 2019-11-01 17:50


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_metadata', '0208_make_course_has_ofac_restrictions_nullable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='additional_information',
            field=models.TextField(blank=True, null=True, default=None, verbose_name='Additional Information'),
        ),
        migrations.AlterField(
            model_name='historicalcourse',
            name='additional_information',
            field=models.TextField(blank=True, null=True, default=None, verbose_name='Additional Information'),
        ),
    ]
