# Generated by Django 3.0.2 on 2020-01-25 18:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0030_auto_20200126_0213'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='coupon',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='downloader.Coupon'),
        ),
    ]
