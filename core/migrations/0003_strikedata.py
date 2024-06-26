# Generated by Django 3.1.4 on 2024-04-14 08:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_intradaydata_symbol'),
    ]

    operations = [
        migrations.CreateModel(
            name='StrikeData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=50, null=True)),
                ('strikePrice', models.IntegerField(blank=True, null=True)),
                ('ce_coi', models.IntegerField(blank=True, null=True)),
                ('ce_volume', models.IntegerField(blank=True, null=True)),
                ('time', models.DateTimeField(blank=True, null=True)),
                ('ce_iv', models.IntegerField(blank=True, null=True)),
                ('ce_tbq', models.IntegerField(blank=True, null=True)),
                ('ce_tsq', models.IntegerField(blank=True, null=True)),
                ('pe_coi', models.IntegerField(blank=True, null=True)),
                ('pe_volume', models.IntegerField(blank=True, null=True)),
                ('pe_iv', models.IntegerField(blank=True, null=True)),
                ('pe_tbq', models.IntegerField(blank=True, null=True)),
                ('pe_tsq', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'strike_data',
            },
        ),
    ]
