from django.core.management.base import BaseCommand, CommandError
from django.db import router, transaction
from wagtail.models import Page, Site

from homepage.portfolio.models import PortfolioIndexPage, ProjectCategory

CATEGORIES = ("Web", "Digital", "Print", "Illustration")


class Command(BaseCommand):
    help = (
        "Create the project categories and, with --create, an empty portfolio page. "
        "Editorial content is entered in the Wagtail admin; existing content is never changed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--create",
            action="store_true",
            help="Create a draft portfolio page at the requested site or path if needed.",
        )
        parser.add_argument("--slug", help="Slug for the page created by --create (defaults to portfolio).")
        parser.add_argument(
            "--hostname",
            help=(
                "With --create: create the page as root page of a new Wagtail site for this hostname "
                "(e.g. design.wersdoerfer.de) instead of below the default site."
            ),
        )
        parser.add_argument(
            "--port",
            type=int,
            default=443,
            help="Port of the Wagtail site created with --hostname (443 for HTTPS, e.g. 8000 locally).",
        )

    def handle(self, *args, create, slug=None, hostname=None, port=443, **options):
        alias = router.db_for_write(Page)
        with transaction.atomic(using=alias):
            self._ensure_portfolio(alias, create, slug, hostname, port)
            for name in CATEGORIES:
                ProjectCategory.objects.using(alias).get_or_create(name=name)

    def _ensure_portfolio(self, alias, create, slug, hostname, port):
        portfolios = PortfolioIndexPage.objects.using(alias)
        missing_page = "No portfolio page exists. Create one in the Wagtail admin or pass --create."
        if not create and not hostname:
            if not portfolios.exists():
                raise CommandError(missing_page)
            return

        sites = Site.objects.using(alias)
        # Treebeard locks during insertion, but the destination check must also
        # run while holding the parent lock.
        if hostname:
            if create:
                parent = Page.get_root_nodes().using(alias).select_for_update().first()
                if parent is None:
                    raise CommandError("No Wagtail page tree root configured.")
            site_conflict = (
                f"A Wagtail site for {hostname}:{port} already exists. "
                "Its root does not match the requested portfolio."
            )
            site = sites.filter(hostname=hostname, port=port).first()
            if site is not None:
                existing = portfolios.filter(pk=site.root_page_id)
                if slug:
                    existing = existing.filter(slug=slug)
                if existing.exists():
                    return
                raise CommandError(site_conflict)
            if not create:
                raise CommandError(missing_page)
        else:
            site = sites.filter(is_default_site=True).first()
            if site is None:
                raise CommandError("No default Wagtail site configured.")
            parent = Page.objects.using(alias).select_for_update().filter(pk=site.root_page_id).first()
            if parent is None:
                raise CommandError("No default Wagtail site root configured.")
            slug = slug or "portfolio"
            if portfolios.filter(pk=parent.pk).exists():
                return
            children = parent.get_children().using(alias).filter(slug=slug)
            occupied = children.exclude(pk__in=portfolios.values("pk")).first()
            if occupied is not None:
                raise CommandError(f"Slug {slug!r} is already occupied by page {occupied.pk} ({occupied.url_path}).")
            if children.exists():
                return

        # Wagtail assigns a unique sibling slug if none was supplied for a dedicated site.
        page = parent.add_child(instance=PortfolioIndexPage(title="Portfolio", slug=slug or "", live=False))
        if hostname:
            site, _ = sites.get_or_create(
                hostname=hostname, port=port, defaults={"root_page": page, "site_name": page.title}
            )
            if site.root_page_id != page.pk:
                raise CommandError(site_conflict)
        page.save_revision()
        receipt = f"Created {page.title} ({page.url_path})"
        transaction.on_commit(lambda: self.stdout.write(receipt), using=alias)
