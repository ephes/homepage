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
    url(r'^images/?$', views.BlogImageListView.as_view(),
        name='image_list'),
    url(r'^images/(?P<pk>\d+)/?$', views.BlogImageDetailView.as_view(),
        name='image_detail'),
    url(
        regex=r'^upload_image/$',
        view=views.ImageCreateView.as_view(),
        name='upload_image'
    ),

    # gallery
    url(r'^gallery/?$', views.BlogGalleryListView.as_view(),
        name='gallery_list'),
    url(r'^gallery/(?P<pk>\d+)/?$', views.BlogGalleryDetailView.as_view(),
        name='gallery_detail'),

    # video
    url(r'^videos/?$', views.BlogVideoListView.as_view(),
        name='video_list'),
    url(r'^videos/(?P<pk>\d+)/?$', views.BlogVideoDetailView.as_view(),
        name='video_detail'),
    url(
        regex=r'^upload_video/$',
        view=views.VideoCreateView.as_view(),
        name='upload_video'
    ),
]
