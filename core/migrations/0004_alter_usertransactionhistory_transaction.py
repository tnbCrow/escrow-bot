# Generated by Django 3.2.7 on 2021-10-27 03:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20210916_2142'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usertransactionhistory',
            name='transaction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='core.transaction'),
        ),
    ]
