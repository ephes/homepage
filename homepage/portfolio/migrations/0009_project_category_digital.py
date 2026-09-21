from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portfolio", "0008_portfolio_contact_heading_primary")]

    operations = [
        migrations.AlterField(
            model_name="projectpage",
            name="category",
            field=models.CharField(
                choices=[
                    ("web", "Web"),
                    ("digital", "Digital"),
                    ("print", "Print"),
                    ("illustration", "Illustration"),
                ],
                max_length=20,
            ),
        ),
    ]
