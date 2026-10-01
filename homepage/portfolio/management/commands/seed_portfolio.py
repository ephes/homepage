from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Site

from homepage.portfolio.models import (
    PortfolioAboutItem,
    PortfolioClient,
    PortfolioIndexPage,
    PortfolioService,
    ProjectCategory,
)

SERVICES = (
    (
        "web",
        "Webdesign",
        "Von der Idee bis zur fertigen Website\u00a0— Layout, UX/UI und Umsetzung.",
    ),
    (
        "product",
        "Product\u00a0Design",
        "UX/UI für Apps & digitale Produkte\u00a0— im Team, mit dem Designpart bei mir.",
    ),
    (
        "graphic",
        "Grafikdesign",
        "Editorial, Layout und Typografie mit Blick fürs Detail.",
    ),
    (
        "branding",
        "Branding",
        "Logo, Marke und Designsysteme, die Wiedererkennung schaffen.",
    ),
    (
        "illustration",
        "Illustration",
        "Handgemachte Bildwelten\u00a0— mein Schwerpunkt und meine Leidenschaft.",
    ),
    (
        "packaging",
        "Verpackung",
        "Packaging, das im Regal auffällt und die Marke trägt.",
    ),
    (
        "campaign",
        "Campaigning",
        "Kampagnenideen und visuelle Leitkonzepte über alle Kanäle.",
    ),
    (
        "ai",
        "KI-Workflows",
        "KI als Sparringspartner im Prozess\u00a0— von Konzept bis Bildwelt.",
    ),
)

ABOUT_ITEMS = (
    (
        "Verstehen",
        "Marken, Menschen und neue Themen.",
        "Mich interessiert, was eine Marke ausmacht und was Gestaltung für sie leisten kann. "
        "Beruflich ging es im Dialogmarketing los. Die Frage „Für wen ist das gedacht?“ begleitet "
        "mich seitdem. Die Erfahrung aus unterschiedlichen Branchen – von Beauty über Food bis "
        "Retail – hilft mir, mich schnell in dein Thema einzuarbeiten und auch ungewohnte Aufgaben "
        "mit frischem Blick zu lösen.",
    ),
    (
        "Gestalten",
        "Illustration, Medien und die Liebe zum Detail.",
        "Illustration begleitet mich schon den ganzen Weg. Ich denke oft in Bildern – und setze sie "
        "gern selbst um, wenn das Projekt es braucht. Über die Jahre habe ich aus Neugier vieles "
        "ausprobiert und dazugelernt. So kann ich heute einen Auftritt über verschiedene Medien "
        "hinweg gestalten und bis ins Detail ausarbeiten. Dabei habe ich schon beim Entwerfen im "
        "Blick, wie es sich umsetzen lässt.",
    ),
    (
        "Umsetzen",
        "Mit Entwicklung und Netzwerk bis zum fertigen Projekt.",
        "Im Team arbeite ich am liebsten – zum Beispiel mit meinem Mann Jochen. Er kümmert sich um "
        "die Software hinter dem Design, mit Schwerpunkt auf Backend und Machine Learning. Je nach "
        "Aufgabe können wir auch weitere Kollegen aus unserem Netzwerk dazuholen. Gemeinsam bleiben "
        "wir dran, bis wir ein gutes Konzept auch tatsächlich auf die Straße gebracht haben. Kurze "
        "Wege inklusive.",
    ),
)

CLIENTS = (
    "ALDI Nord",
    "Kerrygold",
    "L'Oréal",
    "Thomy",
    "Maybelline",
    "essie",
    "Weight Watchers",
    "Miele",
    "Yokohama",
    "McCann",
    "Marina Adler",
    "Fabian Heis",
    "Villa Kunterbunt e.V.",
    "Ökologische Tierzucht gGmbH",
    "django chat",
    "GGS Lennéstraße",
)

CATEGORIES = ("Web", "Digital", "Print", "Illustration")


class Command(BaseCommand):
    help = (
        "Fill empty portfolio collections (services, about items, clients) and project categories "
        "with Katharina's default copy. Existing content is never overwritten."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--create",
            action="store_true",
            help="Create a draft portfolio page below the default site's root page if none exists.",
        )
        parser.add_argument("--slug", default="portfolio", help="Slug for the page created by --create.")

    @transaction.atomic
    def handle(self, *args, create, slug, **options):
        for name in CATEGORIES:
            ProjectCategory.objects.get_or_create(name=name)

        pages = list(PortfolioIndexPage.objects.all())
        if not pages and create:
            pages = [self.create_page(slug)]
        if not pages:
            raise CommandError("No portfolio page exists. Create one in the Wagtail admin or pass --create.")

        for page in pages:
            self.seed_page(page)
            self.stdout.write(f"Seeded {page.title} ({page.url_path})")

    def create_page(self, slug):
        site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
        if site is None:
            raise CommandError("No default Wagtail site configured.")
        page = PortfolioIndexPage(title="Katharina Wersdörfer", slug=slug, live=False)
        site.root_page.add_child(instance=page)
        page.save_revision()
        return page

    def seed_page(self, page):
        """Add default child records through a new revision, so Wagtail's editor keeps them."""

        # A live page without pending changes: the database is authoritative and may hold
        # records that no revision contains, so start from it and publish the result.
        # Otherwise build on the editor's latest draft and leave publishing to the editor.
        publish = page.live and not page.has_unpublished_changes
        draft = page.specific if publish else page.get_latest_revision_as_object()
        changed = False
        if not draft.homepage_services.all():
            draft.homepage_services = [
                PortfolioService(sort_order=index, icon=icon, title=title, description=description)
                for index, (icon, title, description) in enumerate(SERVICES)
            ]
            changed = True
        if not draft.about_items.all():
            draft.about_items = [
                PortfolioAboutItem(sort_order=index, title=title, lead=lead, text=text)
                for index, (title, lead, text) in enumerate(ABOUT_ITEMS)
            ]
            changed = True
        if not draft.clients.all():
            draft.clients = [PortfolioClient(sort_order=index, name=name) for index, name in enumerate(CLIENTS)]
            changed = True
        if not changed:
            return
        revision = draft.save_revision()
        if publish:
            revision.publish()
