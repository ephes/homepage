from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from rest_framework.authtoken import views as authtokenviews
from rest_framework.documentation import include_docs_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path("home/", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/", TemplateView.as_view(template_name="pages/about.html"), name="about"
    ),
    path(
        "jochen/",
        TemplateView.as_view(template_name="pages/jochen.html"),
        name="jochen",
    ),
    path(
        "katharina/",
        TemplateView.as_view(template_name="pages/katharina.html"),
        name="katharina",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("homepage.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    # Cast Blog
    path("blogs/", include("cast.urls", namespace="cast")),
    # Threadedcomments
    re_path(r"^show/comments/", include("fluent_comments.urls")),
    # Fulltext Search
    path("search/", include("watson.urls", namespace="watson")),
    # Indieweb
    re_path(r"^indieweb/", include("indieweb.urls")),
    # rest
    re_path(r"^api/api-token-auth/", authtokenviews.obtain_auth_token),
    # url(r'api/', include('homepage.blogs.api.urls', namespace='api')),
    re_path(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    re_path(r"^docs/", include_docs_urls(title="My Blog API service")),
    # Uploads
    path("uploads/", include("filepond.urls", namespace="filepond")),
    # Wagtail
    path(settings.WAGTAILADMIN_BASE_URL, include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("", include(wagtail_urls)),  # default is wagtail
    # robots.txt
    re_path(
        r"^robots.txt",
        lambda x: HttpResponse(
            "User-Agent: *\nDisallow: /*claas", content_type="text/plain"
        ),
        name="robots_file",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
