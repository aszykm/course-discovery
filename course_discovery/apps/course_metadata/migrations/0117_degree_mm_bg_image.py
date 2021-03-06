# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-09-20 16:16


from django.db import migrations
import stdimage.models
from course_discovery.apps.course_metadata.utils import UploadToFieldNamePath


class Migration(migrations.Migration):

    dependencies = [
        ('course_metadata', '0116_auto_20180912_0857'),
    ]

    operations = [
        migrations.AddField(
            model_name='degree',
            name='micromasters_background_image',
            field=stdimage.models.StdImageField(blank=True, help_text='Customized background image for the MicroMasters section.', null=True, upload_to=UploadToFieldNamePath('uuid', path='media/degree_marketing/mm_images/')),
        ),
    ]
