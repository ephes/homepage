"""Exercise real rendered portfolio pages and assets, with every request intercepted."""

import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from django.contrib.staticfiles import finders
from playwright.sync_api import expect, sync_playwright
from wagtail.models import Locale, Page, Site

from homepage.portfolio.models import PortfolioIndexPage, PortfolioSiteSettings, ProjectCategory, ProjectPage


@pytest.fixture
def browser(rendered_portfolio):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--disable-webgl"])
        yield browser
        browser.close()


@pytest.fixture(params=["homepage", "project"])
def rendered_portfolio(request, db, client):
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Synthetic root", slug="root"))
    index = root.add_child(instance=PortfolioIndexPage(title="Example Studio", slug="example", hero_heading="Hello"))
    index.save_revision().publish()
    Site.objects.all().delete()
    site = Site.objects.create(hostname="testserver", root_page=index, is_default_site=True)
    shell = PortfolioSiteSettings.for_site(site)
    shell.brand_name = "Example Studio"
    shell.contact_email = "studio@example.invalid"
    shell.save()
    project = index.add_child(
        instance=ProjectPage(
            title="Example project",
            slug="example-project",
            year=2026,
            category=ProjectCategory.objects.create(name="Synthetic category"),
            teaser_text="<p>Example overview</p>",
            content=[
                {"type": "statement", "value": {"text": "<p>Example statement</p>"}},
                {
                    "type": "challenge_solution",
                    "value": {
                        "challenge": "<p>First challenge</p><p>Second challenge</p>",
                        "solution": "<p>Example solution</p>",
                    },
                },
            ],
        )
    )
    project.save_revision().publish()
    page = index if request.param == "homepage" else project
    response = client.get(page.url)
    assert response.status_code == 200
    return response.content, page.url, "leistungen" if request.param == "homepage" else "case-study"


@pytest.fixture(params=[1280, 390])
def portfolio_page(request, browser, rendered_portfolio):
    html, path, target = rendered_portfolio
    context = browser.new_context(viewport={"width": request.param, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    violations = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def serve(route):
        url = urlsplit(route.request.url)
        if url.netloc != "testserver":
            violations.append(f"Unexpected external resource: {url.netloc}")
            route.abort()
            return
        if url.path.startswith("/static/"):
            filename = finders.find(unquote(url.path.removeprefix("/static/")))
            if not filename:
                violations.append(f"Missing production asset: {url.path}")
                route.abort()
                return
            route.fulfill(
                body=Path(filename).read_bytes(),
                content_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
            )
        elif url.path == path:
            route.fulfill(body=html, content_type="text/html")
        else:
            route.fulfill(status=404, body="Synthetic fixture has no resource here")

    page.route("**/*", serve)
    page.goto(f"http://testserver{path}")
    page.wait_for_function("document.fonts.status === 'loaded'")
    try:
        yield page, target
    finally:
        context.close()
        assert not errors
        assert not violations


def open_menu(page):
    page.locator(".site-nav > summary").click()
    expect(page.locator(".site-nav")).to_have_attribute("open", "")
    expect(page.locator("main")).to_have_js_property("inert", True)


def test_native_link_gestures_are_not_enhanced(portfolio_page):
    page, target = portfolio_page
    open_menu(page)
    results = page.evaluate(
        """(target) => {
      const menu = document.querySelector('.site-nav');
      const link = menu.querySelector(`a[href="#${target}"]`);
      return [
        {ctrlKey:true}, {metaKey:true}, {shiftKey:true}, {altKey:true}, {button:1},
        {target:'_blank'}, {download:''}, {canceled:true},
      ].map(options => {
        link.removeAttribute('target'); link.removeAttribute('download');
        if ('target' in options) link.target = options.target;
        if ('download' in options) link.setAttribute('download', options.download);
        if (options.canceled) link.addEventListener('click', e => e.preventDefault(), {capture:true,once:true});
        let enhanced;
        link.addEventListener('click', e => { enhanced = e.defaultPrevented; e.preventDefault(); }, {once:true});
        link.dispatchEvent(new MouseEvent('click', {bubbles:true,cancelable:true,button:0,...options}));
        return {enhanced, open:menu.open, hash:location.hash};
      });
    }""",
        target,
    )
    assert results == [{"enhanced": False, "open": True, "hash": ""} for _ in range(7)] + [
        {"enhanced": True, "open": True, "hash": ""}
    ]


def test_keyboard_section_activation_hands_focus_to_visible_content(portfolio_page):
    page, target = portfolio_page
    open_menu(page)
    link = page.locator(f'.site-nav a[href="#{target}"]')
    link.focus()
    page.keyboard.press("Enter")
    expect(page.locator(".site-nav")).not_to_have_attribute("open", "")
    expect(page.locator("main")).to_have_js_property("inert", False)
    expect(page.locator(f"#{target}")).to_be_focused()
    assert urlsplit(page.url).fragment == target
    assert page.locator(f"#{target}").evaluate("e => Math.abs(e.getBoundingClientRect().top) < innerHeight")
    page.keyboard.press("Tab")
    assert page.evaluate("!document.activeElement.closest('.site-nav') && document.activeElement !== document.body")
    expect(page.locator(f"#{target}")).not_to_have_attribute("tabindex", "-1")


def test_escape_and_focus_trap_restore_the_page(portfolio_page):
    page, _ = portfolio_page
    open_menu(page)
    summary = page.locator(".site-nav > summary")
    summary.focus()
    page.keyboard.press("Shift+Tab")
    expect(page.locator(".site-nav nav a, .site-nav nav summary").last).to_be_focused()
    page.keyboard.press("Tab")
    expect(summary).to_be_focused()
    page.keyboard.press("Escape")
    expect(summary).to_be_focused()
    expect(page.locator("main")).to_have_js_property("inert", False)
    expect(page.locator(".site-nav nav")).not_to_be_visible()


def test_hover_preview_does_not_change_focus_or_history(portfolio_page):
    page, target = portfolio_page
    open_menu(page)
    summary = page.locator(".site-nav > summary")
    summary.focus()
    page.locator(f'.site-nav a[href="#{target}"]').hover()
    expect(summary).to_be_focused()
    assert urlsplit(page.url).fragment == ""
    expect(page.locator(".site-nav")).to_have_attribute("open", "")


def test_responsive_chapters_relinquish_multitouch(portfolio_page):
    page, target = portfolio_page
    if target != "case-study":
        assert page.locator(".project-stage").count() == 0
        assert not page.evaluate("""() => {
          const e = new WheelEvent('wheel',{deltaY:100,bubbles:true,cancelable:true});
          document.querySelector('main').dispatchEvent(e); return e.defaultPrevented;
        }""")
        return
    page.emulate_media(reduced_motion="no-preference")
    wide = page.viewport_size["width"] == 1280
    assert page.locator(".project-stage").evaluate(
        "e => getComputedStyle(e).gridTemplateColumns.split(' ').length"
    ) == (2 if wide else 1)
    result = page.evaluate("""() => {
      const head = document.querySelector('.project-intro__head');
      const header = document.querySelector('.site-header');
      scrollTo({top:head.getBoundingClientRect().top+scrollY-header.getBoundingClientRect().height,behavior:'instant'});
      const send = (type, ys) => {
        const e = new Event(type,{bubbles:true,cancelable:true});
        Object.defineProperty(e,'touches',{value:ys.map(clientY => ({clientY}))});
        head.dispatchEvent(e); return e.defaultPrevented;
      };
      send('touchstart',[500]);
      const beforeStep = send('touchmove',[496]);
      const multiBefore = send('touchmove',[490,510]);
      const singleAfterMulti = send('touchmove',[400]);
      send('touchcancel',[]);
      send('touchstart',[500]);
      const stepped = send('touchmove',[400]);
      const multiAfter = send('touchmove',[390,510]);
      const singleAfterStepMulti = send('touchmove',[300]);
      send('touchcancel',[]);
      return {beforeStep,multiBefore,singleAfterMulti,stepped,multiAfter,singleAfterStepMulti};
    }""")
    assert result == {
        "beforeStep": wide,
        "multiBefore": False,
        "singleAfterMulti": False,
        "stepped": wide,
        "multiAfter": False,
        "singleAfterStepMulti": False,
    }
    page.emulate_media(reduced_motion="reduce")
    assert not page.evaluate("""() => {
      const e = new WheelEvent('wheel',{deltaY:100,bubbles:true,cancelable:true});
      document.querySelector('.project-stage').dispatchEvent(e); return e.defaultPrevented;
    }""")


def test_ordinary_page_and_external_links_keep_native_navigation(portfolio_page):
    page, target = portfolio_page
    for href in ("/another-page/#section", "https://outside.invalid/#section", "?different=1#" + target):
        open_menu(page)
        result = page.evaluate(
            """({href,target}) => {
          const link = document.querySelector(`.site-nav a[href="#${target}"]`);
          const original = link.getAttribute("href");
          link.href = href;
          let enhanced;
          link.addEventListener('click', e => { enhanced=e.defaultPrevented; e.preventDefault(); }, {once:true});
          link.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,button:0}));
          link.setAttribute("href", original);
          return {enhanced,hash:location.hash};
        }""",
            {"href": href, "target": target},
        )
        assert result == {"enhanced": False, "hash": ""}
        expect(page.locator("main")).to_have_js_property("inert", False)


def test_destination_keeps_author_tabindex_after_blur(portfolio_page):
    page, target = portfolio_page
    destination = page.locator(f"#{target}")
    destination.evaluate("e => e.setAttribute('tabindex', '0')")
    open_menu(page)
    page.locator(f'.site-nav a[href="#{target}"]').focus()
    page.keyboard.press("Enter")
    expect(destination).to_be_focused()
    page.keyboard.press("Tab")
    expect(destination).not_to_be_focused()
    expect(destination).to_have_attribute("tabindex", "0")
