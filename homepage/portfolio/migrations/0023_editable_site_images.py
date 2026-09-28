import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0022_structural_legal_contact"),
        ("wagtailimages", "0027_image_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="legalpagesettings",
            name="imprint_visual_image",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Optionales 4:5-Motiv. Der in der Bildverwaltung gesetzte "
                    "Fokuspunkt wird beim Ausschnitt berücksichtigt; ohne Bild bleibt "
                    "der grafische Platzhalter."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
                verbose_name="Impressum: Illustration",
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="about_portrait_image",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Bild für den Porträtklecks. Der in der Bildverwaltung gesetzte "
                    "Fokuspunkt wird beim 4:5-Ausschnitt berücksichtigt."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
                verbose_name="Porträt",
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="about_portrait_image_alt",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Beschreibt den Bildinhalt knapp für Menschen, die das Bild nicht "
                    "sehen können."
                ),
                max_length=240,
                verbose_name="Alternativtext des Porträts",
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="hero_background_image",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Optionales Motiv für den farbigen Reveal hinter ‚MOIN‘. Der in "
                    "der Bildverwaltung gesetzte Fokuspunkt steuert die Desktop- und "
                    "Mobile-Ausschnitte. Ohne Auswahl bleibt die freigegebene "
                    "generierte Illustration erhalten."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
                verbose_name="Hero-Hintergrundbild",
            ),
        ),
        migrations.AlterField(
            model_name="legalpagesettings",
            name="imprint_visual_label",
            field=models.CharField(
                default="Illustrationsmotiv",
                help_text=(
                    "Alternativtext des gewählten Bildes und sichtbare Beschriftung "
                    "des grafischen Platzhalters."
                ),
                max_length=160,
                verbose_name="Impressum: Bildbeschreibung",
            ),
        ),
    ]
