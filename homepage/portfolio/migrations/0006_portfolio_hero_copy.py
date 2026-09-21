from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0005_portfoliositesettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="portfolioindexpage",
            name="hero_intro_emphasis",
            field=models.CharField(
                default="Web & Digital Design ist mein Zuhause",
                max_length=200,
                verbose_name="Hervorgehobener Einstieg",
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="hero_intro_secondary",
            field=models.TextField(
                blank=True,
                default=(
                    "Ich denke über Medien hinweg – damit Gestaltung genau dort funktioniert, "
                    "wo sie gebraucht wird."
                ),
                verbose_name="Zweiter Einstiegsabsatz",
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="hero_note_heading",
            field=models.CharField(
                default="15+ years in branding.",
                max_length=120,
                verbose_name="Erfahrungsvermerk",
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="hero_note_text",
            field=models.CharField(
                default="Zwischen Kopfkino, Konzept\u00a0und\u00a0Feinschliff.",
                max_length=200,
                verbose_name="Text zum Erfahrungsvermerk",
            ),
        ),
    ]
