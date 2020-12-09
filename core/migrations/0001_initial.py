# Generated by Django 3.1.4 on 2020-12-09 11:18

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CEStockData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('changeinOpenInterest', models.IntegerField(blank=True, null=True)),
                ('strikePrice', models.IntegerField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'ce_stock_data',
            },
        ),
        migrations.CreateModel(
            name='IntradayData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('call', models.IntegerField(blank=True, null=True)),
                ('put', models.IntegerField(blank=True, null=True)),
                ('diff', models.IntegerField(blank=True, null=True)),
                ('time', models.DateTimeField(blank=True, null=True)),
                ('signal', models.CharField(max_length=50, null=True)),
            ],
            options={
                'db_table': 'intraday_data',
            },
        ),
        migrations.CreateModel(
            name='PEStockData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('changeinOpenInterest', models.IntegerField(blank=True, null=True)),
                ('strikePrice', models.IntegerField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'pe_stock_data',
            },
        ),
    ]
