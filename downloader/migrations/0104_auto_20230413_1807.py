# Generated by Django 3.2.16 on 2023-04-13 10:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0103_auto_20221107_0004'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BaiduAccount',
        ),
        migrations.RemoveField(
            model_name='checkinrecord',
            name='user',
        ),
        migrations.RemoveField(
            model_name='csdnaccount',
            name='user',
        ),
        migrations.RemoveField(
            model_name='docconvertrecord',
            name='user',
        ),
        migrations.DeleteModel(
            name='DocerAccount',
        ),
        migrations.DeleteModel(
            name='MbzjAccount',
        ),
        migrations.DeleteModel(
            name='QiantuAccount',
        ),
        migrations.DeleteModel(
            name='TaobaoWenkuAccount',
        ),
        migrations.RemoveField(
            model_name='uploadrecord',
            name='resource',
        ),
        migrations.RemoveField(
            model_name='uploadrecord',
            name='user',
        ),
        migrations.DeleteModel(
            name='CheckInRecord',
        ),
        migrations.DeleteModel(
            name='CsdnAccount',
        ),
        migrations.DeleteModel(
            name='DocConvertRecord',
        ),
        migrations.DeleteModel(
            name='UploadRecord',
        ),
    ]