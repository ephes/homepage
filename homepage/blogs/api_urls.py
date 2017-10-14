from django.conf.urls import url

from rest_framework.schemas import get_schema_view

from . import views

schema_view = get_schema_view(
    title="Blog API",
)


urlpatterns = [
    url(r'^schema/$', schema_view),
    url(r'^$', views.api_root, name='root'),

    # image
    url(r'^images?$', views.BlogImageListView.as_view(),
        name='image-list'),
    url(r'^images/(?P<pk>\d+)/?$', views.BlogImageDetailView.as_view(),
        name='image-detail'),
]
