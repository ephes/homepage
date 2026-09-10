from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Orderable, Page

from .blocks import ProjectBodyBlock


def current_year():
    """Return the current year without baking it into migrations."""

    return date.today().year


def validate_max_three_words(value):
    """Keep the short error-page headline within the approved composition."""

    if len(value.split()) > 3:
        raise ValidationError("Die Überschrift darf höchstens drei Wörter enthalten.")


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

    panels = [
        FieldPanel("headline"),
        FieldPanel("sentence"),
    ]

    class Meta:
        verbose_name = "501-Seite"


class PortfolioContextMixin:
    """Provide the shared, server-rendered portfolio navigation context."""

    def get_portfolio_index(self):
        if isinstance(self, PortfolioIndexPage):
            return self
        return self.get_parent().specific

    def get_portfolio_projects(self, index=None):
        index = index or self.get_portfolio_index()
        return index.get_children().type(ProjectPage).live().public().specific()

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        portfolio_index = self.get_portfolio_index()
        context["portfolio_index"] = portfolio_index
        context["portfolio_projects"] = self.get_portfolio_projects(portfolio_index)
        return context


class PortfolioIndexPage(PortfolioContextMixin, Page):
    """Landing page and parent for Katharina's project pages."""

    template = "portfolio/portfolio_index_page.html"

    hero_heading = models.CharField(max_length=120)
    hero_intro = models.TextField(blank=True)
    about_heading = models.CharField(max_length=120, default="Über mich")
    about_text = RichTextField(blank=True, features=["bold", "italic", "link"])
    contact_heading = models.CharField(max_length=120, default="Lass uns sprechen")
    contact_email = models.EmailField()

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["portfolio.ProjectPage"]
    max_count_per_parent = 1

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("hero_heading"), FieldPanel("hero_intro")],
            heading="Einstieg",
        ),
        MultiFieldPanel(
            [FieldPanel("about_heading"), FieldPanel("about_text")],
            heading="Über mich",
        ),
        MultiFieldPanel(
            [FieldPanel("contact_heading"), FieldPanel("contact_email")],
            heading="Kontakt",
        ),
    ]


class ProjectPage(PortfolioContextMixin, Page):
    """A server-rendered portfolio case study."""

    class Category(models.TextChoices):
        WEB = "web", "Web"
        PRINT = "print", "Print"
        ILLUSTRATION = "illustration", "Illustration"

    template = "portfolio/project_page.html"

    teaser_text = models.TextField(max_length=320)
    category = models.CharField(max_length=20, choices=Category.choices)
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1900), MaxValueValidator(current_year)])
    client = models.CharField("Kunde", max_length=160, blank=True)
    services = models.CharField(
        max_length=240,
        blank=True,
        editable=False,
        help_text="Temporäres Altfeld; wird nach der Template-Migration entfernt.",
    )
    live_url = models.URLField(blank=True)
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
                FieldPanel("client"),
                FieldPanel("live_url"),
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

    def clean(self):
        super().clean()
        errors = {}
        if self.teaser_image_id and not (self.teaser_image_alt or "").strip():
            errors["teaser_image_alt"] = "Bitte ergänze einen Alternativtext für das Teaserbild."
        if self.hero_image_id and not (self.hero_image_alt or "").strip():
            errors["hero_image_alt"] = "Bitte ergänze einen Alternativtext für den Projekt-Hero."
        if errors:
            raise ValidationError(errors)

    def get_service_names(self):
        """Return ordered services, falling back during the legacy transition."""

        service_names = [service.name for service in self.service_items.all()]
        if service_names:
            return service_names
        return [name.strip() for name in self.services.split(",") if name.strip()]

    def get_other_projects(self, projects=None):
        """Return the next two public projects in tree order, with wraparound."""

        projects = list(self.get_portfolio_projects() if projects is None else projects)
        if len(projects) <= 1:
            return []

        try:
            current_index = next(index for index, project in enumerate(projects) if project.pk == self.pk)
        except StopIteration:
            return [project for project in projects if project.pk != self.pk][:2]

        count = min(2, len(projects) - 1)
        return [projects[(current_index + offset) % len(projects)] for offset in range(1, count + 1)]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["other_projects"] = self.get_other_projects(context["portfolio_projects"])
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
