# Generated by Django 5.1.6 on 2025-04-07 15:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0006_alter_ticket_ticket_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='scanned',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='ticket',
            name='used_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='ticket_number',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
