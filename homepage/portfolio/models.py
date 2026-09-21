from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Orderable, Page, Site
from wagtail.rich_text import RichTextMaxLengthValidator

from .blocks import (
    PROJECT_BLOCK_REGION_CASE_STUDY,
    PROJECT_BLOCK_REGION_MEDIA,
    LegalSectionsBlock,
    ProjectBodyBlock,
    get_project_block_region,
)

def current_year():
    """Return the current year without baking it into migrations."""

    return date.today().year


def validate_max_three_words(value):
    """Keep the short error-page headline within the approved composition."""

    if len(value.split()) > 3:
        raise ValidationError("Die Überschrift darf höchstens drei Wörter enthalten.")


def validate_internal_path_or_http_url(value):
    """Accept a root-relative path or a complete HTTP(S) URL."""

    if (
        value.startswith("/")
        and not value.startswith("//")
        and "\\" not in value
        and not any(ord(character) < 32 for character in value)
    ):
        return
    try:
        URLValidator(schemes=["http", "https"])(value)
    except ValidationError as error:
        raise ValidationError(
            "Bitte einen mit / beginnenden Pfad oder eine vollständige HTTP(S)-URL eingeben."
        ) from error


def default_imprint_sections():
    """Return the approved, editable Impressum copy for a new site."""

    return [
        (
            "section",
            {
                "heading": "Anbieterin",
                "copy": [
                    (
                        "paragraph",
                        "<p>Angaben gemäß § 5 Digitale-Dienste-Gesetz (DDG)</p>",
                    ),
                    (
                        "address",
                        "<p>Katharina Wersdörfer<br>Augustastraße 6<br>"
                        "40477 Düsseldorf<br>Deutschland</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Kontakt",
                "copy": [
                    (
                        "contact",
                        {"prefix": "E-Mail:", "label": "", "suffix": ""},
                    )
                ],
            },
        ),
    ]


def default_privacy_sections():
    """Return the approved, editable Datenschutz copy for a new site."""

    return [
        (
            "section",
            {
                "heading": "Verantwortlich",
                "copy": [
                    (
                        "address",
                        "<p>Katharina Wersdörfer<br>Augustastraße 6<br>40477 "
                        "Düsseldorf<br>Deutschland</p>",
                    ),
                    (
                        "contact",
                        {"prefix": "E-Mail:", "label": "", "suffix": ""},
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Websiteabruf",
                "copy": [
                    (
                        "paragraph",
                        "<p>Diese Website wird auf einem selbst betriebenen Server "
                        "bereitgestellt. Beim Aufruf verarbeitet der Webserver technisch "
                        "erforderliche Verbindungsdaten. Dazu können insbesondere "
                        "IP-Adresse, Datum und Uhrzeit des Abrufs, aufgerufene Adresse, "
                        "übertragene Datenmenge, Referrer-Adresse sowie Angaben zu "
                        "Browser und Betriebssystem gehören.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Die Verarbeitung ist erforderlich, um die Website auszuliefern, "
                        "ihre Stabilität und Sicherheit zu gewährleisten und technische "
                        "Störungen oder Angriffe nachvollziehen zu können. Rechtsgrundlage "
                        "ist Art. 6 Abs. 1 lit. f DSGVO. Das berechtigte Interesse liegt im "
                        "sicheren und zuverlässigen Betrieb dieser Website.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Server-Logdaten werden spätestens nach sieben Tagen gelöscht, "
                        "sofern ein sicherheitsrelevantes Ereignis nicht ausnahmsweise "
                        "eine längere Aufbewahrung zur Aufklärung erfordert. Die "
                        "Server-Logdaten werden keinem externen Hosting-Dienstleister "
                        "offengelegt.</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "E-Mail-Kontakt",
                "copy": [
                    (
                        "paragraph",
                        "<p>Wenn Sie per E-Mail Kontakt aufnehmen, verarbeite ich die von "
                        "Ihnen übermittelten Angaben – insbesondere Name, E-Mail-Adresse, "
                        "Nachrichteninhalt und technische Metadaten – ausschließlich, um "
                        "Ihre Anfrage zu bearbeiten und zu beantworten.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Geht es um eine konkrete Projektanfrage oder eine sonstige "
                        "vorvertragliche Maßnahme, ist Art. 6 Abs. 1 lit. b DSGVO die "
                        "Rechtsgrundlage. Für allgemeine Anfragen erfolgt die Verarbeitung "
                        "nach Art. 6 Abs. 1 lit. f DSGVO; das berechtigte Interesse besteht "
                        "in der sachgerechten Beantwortung Ihrer Nachricht.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Die Daten werden gelöscht, sobald die Anfrage abschließend "
                        "bearbeitet ist und keine gesetzlichen Aufbewahrungspflichten oder "
                        "berechtigten Interessen an einer weiteren Speicherung, "
                        "insbesondere zur Geltendmachung oder Abwehr von Ansprüchen, "
                        "entgegenstehen. Kommt ein Vertrag zustande, können vertrags- und "
                        "steuerrechtlich relevante Unterlagen entsprechend den "
                        "gesetzlichen Aufbewahrungsfristen länger gespeichert werden. "
                        "Empfänger können die für den E-Mail-Verkehr eingesetzten "
                        "Auftragsverarbeiter sein.</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Cookies & Tracking",
                "copy": [
                    (
                        "paragraph",
                        "<p>Diese Website setzt keine Cookies ein, speichert keine "
                        "Informationen in Ihrem Endgerät und greift nicht auf dort "
                        "gespeicherte Informationen zu. Es werden keine Analyse-, "
                        "Reichweitenmessungs-, Werbe- oder Profilingdienste verwendet.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Schriften und sonstige Seitenelemente werden lokal "
                        "bereitgestellt. Beim bloßen Besuch der Website werden keine "
                        "Inhalte von Drittanbietern geladen. Daher ist kein "
                        "Einwilligungsbanner erforderlich.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Der E-Mail-Link öffnet lediglich das auf Ihrem Gerät "
                        "eingerichtete E-Mail-Programm. Daten werden erst verarbeitet, "
                        "wenn Sie eine Nachricht absenden.</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Empfänger & Drittland",
                "copy": [
                    (
                        "paragraph",
                        "<p>Eine Weitergabe personenbezogener Daten erfolgt nur, soweit sie "
                        "für die genannten Zwecke erforderlich ist, eine gesetzliche "
                        "Verpflichtung besteht oder Sie eingewilligt haben. Beim Versand "
                        "einer E-Mail werden Daten technisch über die jeweils beteiligten "
                        "E-Mail-Anbieter übertragen.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Eine Übermittlung personenbezogener Daten in Staaten außerhalb "
                        "der Europäischen Union oder des Europäischen Wirtschaftsraums "
                        "durch mich ist nicht vorgesehen.</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Ihre Rechte",
                "copy": [
                    (
                        "paragraph",
                        "<p>Sie haben nach Maßgabe der gesetzlichen Voraussetzungen das "
                        "Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der "
                        "Verarbeitung und Datenübertragbarkeit. Einer Verarbeitung auf "
                        "Grundlage von Art. 6 Abs. 1 lit. f DSGVO können Sie aus Gründen, "
                        "die sich aus Ihrer besonderen Situation ergeben, widersprechen.</p>",
                    ),
                    (
                        "contact",
                        {
                            "prefix": (
                                "Zur Ausübung Ihrer Rechte genügt eine Nachricht an"
                            ),
                            "label": "",
                            "suffix": ".",
                        },
                    ),
                    (
                        "paragraph",
                        "<p>Sie haben außerdem das Recht, sich bei einer "
                        "Datenschutzaufsichtsbehörde zu beschweren. Zuständig ist "
                        "insbesondere die Landesbeauftragte für Datenschutz und "
                        "Informationsfreiheit Nordrhein-Westfalen, Kavalleriestraße 2–4, "
                        "40213 Düsseldorf, "
                        '<a href="https://www.ldi.nrw.de/">www.ldi.nrw.de</a>.</p>',
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Bereitstellung",
                "copy": [
                    (
                        "paragraph",
                        "<p>Sie sind weder gesetzlich noch vertraglich verpflichtet, "
                        "personenbezogene Daten bereitzustellen. Ohne die für eine E-Mail "
                        "erforderlichen Angaben kann eine Anfrage jedoch nicht beantwortet "
                        "werden. Eine automatisierte Entscheidungsfindung einschließlich "
                        "Profiling findet nicht statt.</p>",
                    ),
                    ("note", "Stand: September 2026"),
                ],
            },
        ),
    ]


def default_project_content():
    """Return editable starter sections for a new portfolio project."""

    return [
        (
            "statement",
            {
                "text": (
                    "<p>[Ein prägnanter Satz, der das Projekt und seinen "
                    "gestalterischen Kern erklärt.]</p>"
                )
            },
        ),
        (
            "challenge_solution",
            {
                "challenge": (
                    "<p>[Ausgangslage, Ziel und Rahmenbedingungen. Dieser Bereich "
                    "wird später als redaktionelles Wagtail-Feld gepflegt.]</p>"
                ),
                "solution": (
                    "<p>[Konzept, gestalterische Entscheidungen und Umsetzung. "
                    "Bilder und Textblöcke können im späteren Template einzeln ein- "
                    "oder ausgeblendet werden.]</p>"
                ),
            },
        ),
        (
            "stats",
            {
                "items": [
                    {"value": f"0{number}", "label": "[Ergebnis oder Kennzahl]"}
                    for number in range(1, 5)
                ]
            },
        ),
        (
            "testimonial",
            {
                "quote": "[Optionales Kundenstatement zum Projekt.]",
                "name": "[Name]",
                "role": "[Rolle]",
            },
        ),
    ]


class ErrorPageSettings(BaseSiteSetting):
    """Editable copy for the deterministic HTTP 501 response."""

    headline = models.CharField(
        "Überschrift",
        max_length=120,
        default="Ablage P.",
        validators=[validate_max_three_words],
        help_text="Kurze Überschrift mit höchstens drei Wörtern.",
    )
    sentence = models.CharField(
        "Satz",
        max_length=240,
        default=(
            "Diese Idee hat es leider nicht weiter geschafft. Also zurück ans Zeichenbrett. "
            "Du könntest dir so lange diese Projekte anschauen."
        ),
    )
    code_label = models.CharField(
        "Fehlerkennung",
        max_length=80,
        default="Fehler 501",
    )
    featured_projects_heading = models.CharField(
        "Überschrift der Projektempfehlungen",
        max_length=160,
        default="Projekte zum Weitersehen",
    )
    home_link_label = models.CharField(
        "Beschriftung des Startseitenlinks",
        max_length=120,
        default="Zur Startseite",
    )

    panels = [
        FieldPanel("code_label"),
        FieldPanel("headline"),
        FieldPanel("sentence"),
        FieldPanel("featured_projects_heading"),
        FieldPanel("home_link_label"),
    ]

    class Meta:
        verbose_name = "501-Seite"


class PortfolioSiteSettings(BaseSiteSetting):
    """Shared, per-site content for the portfolio shell.

    The approved prototype repeats these values across the header, navigation,
    footer and utility pages. Keeping the editorial contract here lets shared
    visual-parity templates consume one source without coupling shell content to
    a particular landing-page revision.
    """

    brand_name = models.CharField(
        "Name", max_length=120, default="Katharina Wersdörfer"
    )
    availability_text = models.CharField(
        "Verfügbarkeitstext",
        max_length=120,
        default="Verfügbar für Projekte",
    )
    show_availability = models.BooleanField("Verfügbarkeit anzeigen", default=True)
    profile_text = models.CharField(
        "Kurzprofil",
        max_length=240,
        default="Web & Digital Design, Illustration und Print — aus Düsseldorf.",
    )
    contact_email = models.EmailField(
        "Kontaktadresse",
        default="katharina@wersdoerfer.de",
        help_text=(
            "Einzige öffentliche E-Mail-Quelle für Header, Menü, Startseite, "
            "Projektseiten und Rechtstexte."
        ),
    )
    linkedin_url = models.URLField(
        "LinkedIn",
        blank=True,
        default="https://www.linkedin.com/in/katharina-wersd%C3%B6rfer-7a41181a2",
    )
    github_url = models.URLField(
        "GitHub",
        blank=True,
        default="https://github.com/federfuxx",
    )
    mastodon_url = models.URLField(
        "Mastodon",
        blank=True,
        default="https://fedi.wersdoerfer.de/@katharina",
    )
    imprint_url = models.CharField(
        "Impressum",
        max_length=255,
        default="/impressum/",
        editable=False,
        help_text="Mit / beginnender interner Pfad oder vollständige HTTP(S)-URL.",
        validators=[validate_internal_path_or_http_url],
    )
    privacy_url = models.CharField(
        "Datenschutz",
        max_length=255,
        default="/datenschutz/",
        editable=False,
        help_text="Mit / beginnender interner Pfad oder vollständige HTTP(S)-URL.",
        validators=[validate_internal_path_or_http_url],
    )
    copyright_text = models.CharField(
        "Copyright",
        max_length=160,
        default="© 2026 Katharina Wersdörfer",
    )
    location_text = models.CharField(
        "Ortszeile",
        max_length=160,
        default="Designed in Düsseldorf",
    )
    contact_label = models.CharField(
        "Kontakt",
        max_length=80,
        default="Kontakt",
    )
    projects_label = models.CharField(
        "Projekte",
        max_length=80,
        default="Projekte",
    )
    all_projects_label = models.CharField(
        "Alle Projekte",
        max_length=120,
        default="Alle Projekte",
    )
    services_label = models.CharField(
        "Leistungen",
        max_length=80,
        default="Leistungen",
    )
    about_label = models.CharField(
        "Über mich",
        max_length=80,
        default="Über mich",
    )
    clients_label = models.CharField(
        "Kunden",
        max_length=80,
        default="Kunden",
    )
    case_study_label = models.CharField(
        "Case Study",
        max_length=80,
        default="Case Study",
    )
    gallery_label = models.CharField(
        "Galerie",
        max_length=80,
        default="Galerie",
    )
    results_label = models.CharField(
        "Mehrwert",
        max_length=80,
        default="Mehrwert",
    )
    footer_pages_heading = models.CharField(
        "Footer: Seitenüberschrift",
        max_length=80,
        default="Seite",
    )
    project_kicker = models.CharField(
        "Projekt: Zählerbezeichnung",
        max_length=80,
        default="Projekt",
    )
    project_meta_category_label = models.CharField(
        "Projekt: Bereich",
        max_length=80,
        default="Bereich",
    )
    project_meta_year_label = models.CharField(
        "Projekt: Jahr",
        max_length=80,
        default="Jahr",
    )
    project_meta_client_label = models.CharField(
        "Projekt: Kunde",
        max_length=80,
        default="Kunde",
    )
    project_meta_services_label = models.CharField(
        "Projekt: Leistungen",
        max_length=80,
        default="Leistungen",
    )
    project_live_link_label = models.CharField(
        "Projekt: Link zur Website",
        max_length=120,
        default="Website ansehen",
    )
    project_statement_heading = models.CharField(
        "Projekt: Statement-Überschrift",
        max_length=120,
        default="Das Projekt",
    )
    project_challenge_heading = models.CharField(
        "Projekt: Aufgaben-Überschrift",
        max_length=120,
        default="Die Aufgabe",
    )
    project_solution_heading = models.CharField(
        "Projekt: Lösungs-Überschrift",
        max_length=120,
        default="Die Lösung",
    )
    project_results_heading = models.CharField(
        "Projekt: Mehrwert-Überschrift",
        max_length=120,
        default="Was bleibt.",
    )
    project_testimonial_label = models.CharField(
        "Projekt: Kundenstimmen-Rubrik",
        max_length=120,
        default="Kundenstimmen",
    )
    related_projects_eyebrow = models.CharField(
        "Weitere Projekte: Rubrik",
        max_length=120,
        default="Weitere Projekte",
    )
    related_projects_heading = models.CharField(
        "Weitere Projekte: Überschrift",
        max_length=120,
        default="Weiterse\u00adhen.",
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("brand_name"),
                FieldPanel("availability_text"),
                FieldPanel("show_availability"),
                FieldPanel("profile_text"),
                FieldPanel("contact_email"),
            ],
            heading="Profil und Kontakt",
        ),
        MultiFieldPanel(
            [
                FieldPanel("linkedin_url"),
                FieldPanel("github_url"),
                FieldPanel("mastodon_url"),
            ],
            heading="Soziale Profile",
        ),
        MultiFieldPanel(
            [
                FieldPanel("contact_label"),
                FieldPanel("projects_label"),
                FieldPanel("all_projects_label"),
                FieldPanel("services_label"),
                FieldPanel("about_label"),
                FieldPanel("clients_label"),
                FieldPanel("case_study_label"),
                FieldPanel("gallery_label"),
                FieldPanel("results_label"),
            ],
            heading="Navigation",
        ),
        MultiFieldPanel(
            [
                FieldPanel("project_kicker"),
                FieldPanel("project_meta_category_label"),
                FieldPanel("project_meta_year_label"),
                FieldPanel("project_meta_client_label"),
                FieldPanel("project_meta_services_label"),
                FieldPanel("project_live_link_label"),
                FieldPanel("project_statement_heading"),
                FieldPanel("project_challenge_heading"),
                FieldPanel("project_solution_heading"),
                FieldPanel("project_results_heading"),
                FieldPanel("project_testimonial_label"),
                FieldPanel("related_projects_eyebrow"),
                FieldPanel("related_projects_heading"),
            ],
            heading="Projektseiten",
        ),
        MultiFieldPanel(
            [
                FieldPanel("footer_pages_heading"),
                FieldPanel("copyright_text"),
                FieldPanel("location_text"),
            ],
            heading="Footerleiste",
        ),
    ]

    class Meta:
        verbose_name = "Portfolio-Site"


class LegalPageSettings(BaseSiteSetting):
    """Per-site, semantically structured copy for the two legal pages."""

    eyebrow = models.CharField("Rubrik", max_length=120, default="Rechtliches")
    imprint_title = models.CharField(
        "Impressum: Seitentitel",
        max_length=120,
        default="Impressum",
    )
    imprint_sections = StreamField(
        LegalSectionsBlock(),
        default=default_imprint_sections,
        verbose_name="Impressum: Abschnitte",
    )
    imprint_visual_label = models.CharField(
        "Impressum: Bildplatzhalter",
        max_length=160,
        default="Illustrationsmotiv",
    )
    privacy_title = models.CharField(
        "Datenschutz: Seitentitel",
        max_length=120,
        default="Datenschutz",
    )
    privacy_sections = StreamField(
        LegalSectionsBlock(),
        default=default_privacy_sections,
        verbose_name="Datenschutz: Abschnitte",
    )

    panels = [
        FieldPanel("eyebrow"),
        MultiFieldPanel(
            [
                FieldPanel("imprint_title"),
                FieldPanel("imprint_sections"),
                FieldPanel("imprint_visual_label"),
            ],
            heading="Impressum",
        ),
        MultiFieldPanel(
            [FieldPanel("privacy_title"), FieldPanel("privacy_sections")],
            heading="Datenschutz",
        ),
    ]

    class Meta:
        verbose_name = "Portfolio-Rechtsseiten"


def get_site_setting_or_default(setting_model, site, **unsaved_values):
    """Return saved site settings or an unsaved instance with field defaults."""

    if site is None:
        return setting_model(**unsaved_values)
    return setting_model.objects.filter(site=site).first() or setting_model(
        site=site, **unsaved_values
    )


class PortfolioContextMixin:
    """Provide the shared, server-rendered portfolio navigation context."""

    def get_portfolio_index(self):
        if isinstance(self, PortfolioIndexPage):
            return self
        return self.get_parent().specific

    def get_portfolio_projects(self, index=None):
        index = index or self.get_portfolio_index()
        return (
            ProjectPage.objects.child_of(index)
            .live()
            .public()
            .select_related("category")
        )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        portfolio_index = self.get_portfolio_index()
        site = Site.find_for_request(request) or self.get_site()
        context["portfolio_index"] = portfolio_index
        context["portfolio_projects"] = list(
            self.get_portfolio_projects(portfolio_index)
        )
        context["portfolio_site_settings"] = get_site_setting_or_default(
            PortfolioSiteSettings, site
        )
        context["portfolio_legal_settings"] = get_site_setting_or_default(
            LegalPageSettings,
            site,
            imprint_sections=[],
            privacy_sections=[],
        )
        return context


class PortfolioIndexPage(PortfolioContextMixin, Page):
    """Landing page and parent for Katharina's project pages."""

    template = "portfolio/portfolio_index_page.html"
    admin_default_ordering = "ord"

    hero_heading = models.CharField(max_length=120, default="Moin", editable=False)
    hero_intro_emphasis = models.CharField(
        "Hervorgehobener Einstieg",
        max_length=200,
        default="Web & Digital Design ist mein Zuhause",
    )
    hero_intro = models.TextField(blank=True)
    hero_intro_secondary = models.TextField(
        "Zweiter Einstiegsabsatz",
        blank=True,
        default=(
            "Ich denke über Medien hinweg – damit Gestaltung genau dort funktioniert, "
            "wo sie gebraucht wird."
        ),
    )
    hero_note_heading = models.CharField(
        "Erfahrungsvermerk",
        max_length=120,
        default="15+ years in branding.",
    )
    hero_note_text = models.CharField(
        "Text zum Erfahrungsvermerk",
        max_length=200,
        default="Zwischen Kopfkino, Konzept\u00a0und\u00a0Feinschliff.",
    )
    about_heading = models.CharField(
        max_length=120,
        default="Über mich",
        editable=False,
        help_text=(
            "Historisches Kompatibilitätsfeld. Die sichtbaren Inhalte werden über "
            "die editierbaren Über-mich-Einträge gepflegt."
        ),
    )
    about_text = RichTextField(
        blank=True,
        features=["bold", "italic", "link"],
        editable=False,
        help_text=(
            "Historisches Kompatibilitätsfeld. Die sichtbaren Inhalte werden über "
            "die editierbaren Über-mich-Einträge gepflegt."
        ),
    )
    contact_heading = models.CharField(
        max_length=120,
        default="Lass uns sprechen",
        editable=False,
        help_text=(
            "Historisches Kompatibilitätsfeld. Die sichtbare Kontaktüberschrift "
            "wird über die getrennten Kontaktfelder gepflegt."
        ),
    )
    contact_email = models.EmailField(
        default="katharina@wersdoerfer.de",
        editable=False,
        help_text=(
            "Historisches Kompatibilitätsfeld. Die öffentliche Kontaktadresse wird "
            "ausschließlich in den Portfolio-Site-Einstellungen gepflegt."
        ),
    )
    projects_eyebrow = models.CharField(max_length=120, default="Ein kleiner Einblick")
    projects_heading = models.CharField(max_length=120, default="Projekte")
    projects_annotation = models.CharField(
        max_length=120, default="recent work", editable=False
    )
    project_inquiry_label = models.CharField(max_length=120, default="Projekt anfragen")
    services_eyebrow = models.CharField(max_length=120, default="Was ich anbiete")
    services_heading = models.CharField(max_length=120, default="Leistungen")
    services_annotation = models.CharField(
        max_length=120, default="let's talk about", editable=False
    )
    about_eyebrow = models.CharField(max_length=120, default="Wie ich arbeite")
    about_statement_intro = models.CharField(max_length=120, default="Ich bin")
    about_name = models.CharField(max_length=120, default="Katharina")
    about_statement_outro = models.CharField(
        max_length=160, default="und bleibe gern neugierig."
    )
    about_annotation = models.CharField(
        max_length=120, default="that's me", editable=False
    )
    about_claim = models.CharField(
        max_length=160, default="Digital Creative · Based in Düsseldorf"
    )
    resume_label = models.CharField(max_length=120, default="Lebenslauf anfragen")
    clients_eyebrow = models.CharField(max_length=120, default="Über die Jahre")
    clients_heading = models.CharField(max_length=160, default="Mit diesen Marken")
    clients_heading_secondary = models.CharField(max_length=160, default="& Menschen")
    clients_annotation = models.CharField(
        max_length=120, default="together", editable=False
    )
    contact_eyebrow = models.CharField(max_length=120, default="Auf ein Wort")
    contact_heading_primary = models.CharField(
        max_length=160, default="Ein Projekt im Kopf?"
    )
    contact_heading_secondary = models.CharField(max_length=160, default="Schreib")
    contact_heading_emphasis = models.CharField(max_length=80, default="mir.")
    contact_annotation = models.CharField(
        max_length=120, default="tell me more", editable=False
    )
    contact_cta_label = models.CharField(max_length=120, default="E-Mail schreiben")

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["portfolio.ProjectPage"]
    max_count_per_parent = 1

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_note_heading"),
                FieldPanel("hero_note_text"),
                FieldPanel("hero_intro_emphasis"),
                FieldPanel("hero_intro"),
                FieldPanel("hero_intro_secondary"),
            ],
            heading="Einstieg",
        ),
        MultiFieldPanel(
            [
                FieldPanel("projects_eyebrow"),
                FieldPanel("projects_heading"),
                FieldPanel("project_inquiry_label"),
            ],
            heading="Projektübersicht",
        ),
        MultiFieldPanel(
            [
                FieldPanel("services_eyebrow"),
                FieldPanel("services_heading"),
            ],
            heading="Leistungen",
        ),
        InlinePanel("homepage_services", label="Leistung", heading="Leistungen"),
        MultiFieldPanel(
            [
                FieldPanel("about_eyebrow"),
                FieldPanel("about_statement_intro"),
                FieldPanel("about_name"),
                FieldPanel("about_statement_outro"),
                FieldPanel("about_claim"),
                FieldPanel("resume_label"),
            ],
            heading="Arbeitsweise",
        ),
        InlinePanel("about_items", label="Abschnitt", heading="Arbeitsweise"),
        MultiFieldPanel(
            [
                FieldPanel("clients_eyebrow"),
                FieldPanel("clients_heading"),
                FieldPanel("clients_heading_secondary"),
            ],
            heading="Kunden",
        ),
        InlinePanel("clients", label="Name", heading="Kundenliste"),
        MultiFieldPanel(
            [
                FieldPanel("contact_eyebrow"),
                FieldPanel("contact_heading_primary"),
                FieldPanel("contact_heading_secondary"),
                FieldPanel("contact_heading_emphasis"),
                FieldPanel("contact_cta_label"),
            ],
            heading="Kontaktgestaltung",
        ),
    ]


class PortfolioService(Orderable):
    """An editor-sortable service in the approved homepage composition."""

    class Icon(models.TextChoices):
        WEB = "web", "Webdesign"
        PRODUCT = "product", "Product Design"
        GRAPHIC = "graphic", "Grafikdesign"
        BRANDING = "branding", "Branding"
        ILLUSTRATION = "illustration", "Illustration"
        PACKAGING = "packaging", "Verpackung"
        CAMPAIGN = "campaign", "Campaigning"
        AI = "ai", "KI-Workflows"

    page = ParentalKey(
        PortfolioIndexPage,
        on_delete=models.CASCADE,
        related_name="homepage_services",
    )
    icon = models.CharField(max_length=20, choices=Icon.choices)
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=320)

    panels = [FieldPanel("icon"), FieldPanel("title"), FieldPanel("description")]


class PortfolioAboutItem(Orderable):
    """One semantic disclosure row in the homepage profile section."""

    page = ParentalKey(
        PortfolioIndexPage,
        on_delete=models.CASCADE,
        related_name="about_items",
    )
    title = models.CharField(max_length=120)
    lead = models.CharField(max_length=240)
    text = models.TextField()

    panels = [FieldPanel("title"), FieldPanel("lead"), FieldPanel("text")]


class PortfolioClient(Orderable):
    """One editor-sortable client name for the accessible marquee source list."""

    page = ParentalKey(
        PortfolioIndexPage,
        on_delete=models.CASCADE,
        related_name="clients",
    )
    name = models.CharField(max_length=160)

    panels = [FieldPanel("name")]


class ProjectCategory(models.Model):
    """A centrally managed category shared by any number of projects."""

    name = models.CharField("Name", max_length=80, unique=True)

    panels = [FieldPanel("name")]

    class Meta:
        ordering = ["name"]
        verbose_name = "Projektkategorie"
        verbose_name_plural = "Projektkategorien"

    def __str__(self):
        return self.name


class ProjectPage(PortfolioContextMixin, Page):
    """A server-rendered portfolio case study."""

    class LegacyCategory(models.TextChoices):
        WEB = "web", "Web"
        DIGITAL = "digital", "Digital"
        PRINT = "print", "Print"
        ILLUSTRATION = "illustration", "Illustration"

    template = "portfolio/project_page.html"

    teaser_text = RichTextField(
        "Teasertext",
        features=["bold", "link", "no-break"],
        max_length=320,
        help_text=(
            "Kurzer Projektteaser; Hervorhebungen können fett gesetzt, verlinkt oder "
            "mit ‚Kein Umbruch‘ als zusammenhängender Begriff geschützt werden."
        ),
    )
    category_legacy = models.CharField(
        max_length=20,
        choices=LegacyCategory.choices,
        blank=True,
        default="",
        editable=False,
        help_text="Temporäres Altfeld; wird nach geprüfter Inhaltsmigration entfernt.",
    )
    category = models.ForeignKey(
        ProjectCategory,
        on_delete=models.PROTECT,
        related_name="projects",
        verbose_name="Bereich",
        help_text=(
            "Zentrale Projektkategorie. Neue Kategorien können direkt im Auswahlfenster "
            "oder über ‚Projekte → Kategorien‘ angelegt werden."
        ),
    )
    year = models.PositiveSmallIntegerField(
        "Jahr / Startjahr",
        validators=[MinValueValidator(1900), MaxValueValidator(current_year)],
        help_text="Bei einem Zeitraum das erste Jahr eintragen.",
    )
    end_year = models.PositiveSmallIntegerField(
        "Endjahr (optional)",
        null=True,
        blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(current_year)],
        help_text=(
            "Nur bei mehrjährigen Projekten ausfüllen. "
            "Die Ausgabe erfolgt automatisch als Zeitraum, zum Beispiel 2021–2024."
        ),
    )
    homepage_is_hero = models.BooleanField(
        "Hero-Kachel auf der Startseite",
        default=False,
        help_text=(
            "Stellt das Projekt im Desktop-Raster groß und quer im Format 21:9 dar. "
            "Mobil bleibt das erste Projekt der sortierten Reihenfolge der große "
            "16:9-Einstieg; alle weiteren Projekte laufen im einheitlichen Reel."
        ),
    )
    client = models.CharField("Kunde", max_length=160, blank=True)
    services = models.CharField(
        max_length=240,
        blank=True,
        editable=False,
        help_text="Temporäres Altfeld; wird nach der Template-Migration entfernt.",
    )
    live_url = models.URLField(blank=True)
    live_link_label = models.CharField(
        "Text des Website-Buttons",
        max_length=120,
        blank=True,
        default="",
        help_text=(
            "Optionaler Text für den Link zur Projektwebsite. Leer lassen, um den "
            "globalen Standard zu verwenden."
        ),
    )
    teaser_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Während der Datenmigration noch optional; vor dem finalen Launch erforderlich machen.",
    )
    teaser_image_alt = models.CharField(
        "Alternativtext des Teaserbilds",
        max_length=240,
        blank=True,
        help_text="Beschreibt den Bildinhalt knapp für Menschen, die das Bild nicht sehen können.",
    )
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Projekt-Hero",
        help_text="Während der Datenmigration noch optional; vor dem finalen Launch erforderlich machen.",
    )
    hero_image_alt = models.CharField(
        "Alternativtext des Projekt-Heros",
        max_length=240,
        blank=True,
        help_text="Beschreibt den Bildinhalt knapp für Menschen, die das Bild nicht sehen können.",
    )
    body = RichTextField(
        blank=True,
        editable=False,
        features=["h2", "h3", "bold", "italic", "ol", "ul", "link"],
        help_text="Temporäres Altfeld; wird nach der Template-Migration entfernt.",
    )
    content = StreamField(
        ProjectBodyBlock(),
        blank=True,
        default=default_project_content,
        block_counts={
            "statement": {"max_num": 1},
            "challenge_solution": {"max_num": 1},
            "stats": {"max_num": 1},
            "testimonial": {"max_num": 1},
        },
        verbose_name="Projektinhalt",
    )

    parent_page_types = ["portfolio.PortfolioIndexPage"]
    subpage_types = []

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("teaser_text"),
                FieldPanel("category"),
                FieldPanel("year"),
                FieldPanel("end_year"),
                FieldPanel("homepage_is_hero"),
                FieldPanel("client"),
                FieldPanel("live_url"),
                FieldPanel("live_link_label"),
                FieldPanel("teaser_image"),
                FieldPanel("teaser_image_alt"),
                FieldPanel("hero_image"),
                FieldPanel("hero_image_alt"),
            ],
            heading="Projektübersicht",
        ),
        InlinePanel(
            "service_items",
            label="Leistung",
            heading="Leistungen",
            min_num=1,
        ),
        FieldPanel("content"),
    ]

    def clean_fields(self, exclude=None):
        errors = {}
        try:
            super().clean_fields(exclude=exclude)
        except ValidationError as error:
            error.update_error_dict(errors)

        # RichTextField applies its visible-text limit in the Wagtail formfield, not
        # during model validation. Validate non-form writes here while respecting the
        # form's excluded fields so editors do not receive the same error twice.
        if "teaser_text" not in (exclude or ()):
            try:
                teaser_limit = self._meta.get_field("teaser_text").max_length
                RichTextMaxLengthValidator(teaser_limit)(self.teaser_text)
            except ValidationError as error:
                ValidationError({"teaser_text": error}).update_error_dict(errors)

        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        errors = {}
        if self.teaser_image_id and not (self.teaser_image_alt or "").strip():
            errors["teaser_image_alt"] = (
                "Bitte ergänze einen Alternativtext für das Teaserbild."
            )
        if self.hero_image_id and not (self.hero_image_alt or "").strip():
            errors["hero_image_alt"] = (
                "Bitte ergänze einen Alternativtext für den Projekt-Hero."
            )
        if self.end_year is not None and self.year is not None:
            if self.end_year < self.year:
                errors["end_year"] = (
                    "Das Endjahr darf nicht vor dem Jahr / Startjahr liegen."
                )
        if errors:
            raise ValidationError(errors)

    @property
    def year_display(self):
        """Return one year or the inclusive editorial project period."""

        if self.end_year is None or self.end_year == self.year:
            return str(self.year)
        return f"{self.year}–{self.end_year}"

    def get_service_names(self):
        """Return ordered services, falling back during the legacy transition."""

        service_names = [service.name for service in self.service_items.all()]
        if service_names:
            return service_names
        return [name.strip() for name in self.services.split(",") if name.strip()]

    def get_category_display(self):
        """Keep the established template API while categories become editable."""

        if self.category_id:
            return self.category.name
        if self.category_legacy:
            return self.LegacyCategory(self.category_legacy).label
        return ""

    def get_other_projects(self, projects=None):
        """Return the next two public projects in tree order, with wraparound."""

        projects = list(self.get_portfolio_projects() if projects is None else projects)
        if len(projects) <= 1:
            return []

        try:
            current_index = next(
                index for index, project in enumerate(projects) if project.pk == self.pk
            )
        except StopIteration:
            return [project for project in projects if project.pk != self.pk][:2]

        count = min(2, len(projects) - 1)
        return [
            projects[(current_index + offset) % len(projects)]
            for offset in range(1, count + 1)
        ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["other_projects"] = self.get_other_projects(
            context["portfolio_projects"]
        )
        project_block_types = {block.block_type for block in self.content}
        numbered_projects = list(context["portfolio_projects"])
        try:
            project_number = next(
                index
                for index, project in enumerate(numbered_projects, start=1)
                if project.pk == self.pk
            )
        except StopIteration:
            # Preview the current draft in its public context without letting
            # unrelated drafts change the counter visitors will eventually see.
            numbered_projects = sorted(
                [*numbered_projects, self], key=lambda project: project.path
            )
            project_number = next(
                (
                    index
                    for index, project in enumerate(numbered_projects, start=1)
                    if project.pk == self.pk
                ),
                1,
            )
        context.update(
            {
                "project_has_case_study": bool(
                    any(
                        get_project_block_region(block_type)
                        == PROJECT_BLOCK_REGION_CASE_STUDY
                        for block_type in project_block_types
                    )
                ),
                "project_has_editorial_media": bool(
                    any(
                        get_project_block_region(block_type)
                        == PROJECT_BLOCK_REGION_MEDIA
                        for block_type in project_block_types
                    )
                ),
                "project_has_results": "stats" in project_block_types,
                "project_number": project_number,
                "project_total": len(numbered_projects),
            }
        )
        return context


class ProjectService(Orderable):
    """An editor-sortable service attached to one portfolio project."""

    page = ParentalKey(
        ProjectPage,
        on_delete=models.CASCADE,
        related_name="service_items",
    )
    name = models.CharField("Leistung", max_length=240)

    panels = [FieldPanel("name")]

    def __str__(self):
        return self.name
