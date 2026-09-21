from django.db import migrations, models


def split_approved_contact_heading(apps, schema_editor):
    PortfolioIndexPage = apps.get_model("portfolio", "PortfolioIndexPage")
    database = schema_editor.connection.alias
    PortfolioIndexPage.objects.using(database).filter(
        contact_heading_secondary="Schreib mir."
    ).update(contact_heading_secondary="Schreib")


def restore_approved_contact_heading(apps, schema_editor):
    PortfolioIndexPage = apps.get_model("portfolio", "PortfolioIndexPage")
    database = schema_editor.connection.alias
    PortfolioIndexPage.objects.using(database).filter(
        contact_heading_secondary="Schreib",
        contact_heading_emphasis="mir.",
    ).update(contact_heading_secondary="Schreib mir.")


class Migration(migrations.Migration):
    dependencies = [("portfolio", "0009_project_category_digital")]

    operations = [
        migrations.AlterField(
            model_name="portfolioindexpage",
            name="contact_heading_secondary",
            field=models.CharField(default="Schreib", max_length=160),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="contact_heading_emphasis",
            field=models.CharField(default="mir.", max_length=80),
        ),
        migrations.RunPython(
            split_approved_contact_heading,
            restore_approved_contact_heading,
        ),
    ]
