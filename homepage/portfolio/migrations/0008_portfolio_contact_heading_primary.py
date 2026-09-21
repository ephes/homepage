from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portfolio", "0007_homepage_parity_content")]

    operations = [
        migrations.AddField(
            model_name="portfolioindexpage",
            name="contact_heading_primary",
            field=models.CharField(default="Ein Projekt im Kopf?", max_length=160),
        ),
    ]
