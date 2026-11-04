from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='keshtyar_sale_id',
            field=models.PositiveIntegerField(
                blank=True, null=True, unique=True, verbose_name='شناسه اعلام فروش کشت‌یار',
            ),
        ),
    ]
