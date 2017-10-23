import logging

from collections import OrderedDict

from django.views.generic import CreateView

from django.contrib.auth.mixins import LoginRequiredMixin

from django.core.urlresolvers import reverse

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .serializers import (
    BlogImageSerializer,
    BlogVideoSerializer,
    BlogGallerySerializer,
)

from ..forms import (
    BlogImageForm,
    BlogVideoForm,
)

from ..viewmixins import AddRequestUserMixin
from .viewmixins import FileUploadResponseMixin

from ..models import (
    BlogImage,
    BlogVideo,
    BlogGallery,
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
def api_root(request):
    """
    Show API contents.
    If you add any object types, add them here!
    """
    root_api_urls = (
        ('images',
         request.build_absolute_uri(reverse('api:image-list'))),
        ('galleries',
         request.build_absolute_uri(reverse('api:gallery-list'))),
        ('videos',
         request.build_absolute_uri(reverse('api:video-list'))),
    )
    print(root_api_urls)
    return Response(OrderedDict(root_api_urls))


class ImageCreateView(LoginRequiredMixin, AddRequestUserMixin,
                      FileUploadResponseMixin, CreateView):
    model = BlogImage
    form_class = BlogImageForm
    user_field_name = 'user'


class VideoCreateView(LoginRequiredMixin, AddRequestUserMixin,
                      FileUploadResponseMixin, CreateView):
    model = BlogVideo
    form_class = BlogVideoForm
    user_field_name = 'user'


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 10000


class BlogImageListView(generics.ListCreateAPIView):
    serializer_class = BlogImageSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        qs = BlogImage.objects.all().filter(user=user)
        return qs.order_by('-created')


class BlogImageDetailView(generics.RetrieveDestroyAPIView):
    queryset = BlogImage.objects.all()
    serializer_class = BlogImageSerializer
    permission_classes = (IsAuthenticated,)


class BlogVideoListView(generics.ListCreateAPIView):
    serializer_class = BlogVideoSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        qs = BlogVideo.objects.all().filter(user=user)
        return qs.order_by('-created')


class BlogVideoDetailView(generics.RetrieveDestroyAPIView):
    queryset = BlogVideo.objects.all()
    serializer_class = BlogVideoSerializer
    permission_classes = (IsAuthenticated,)


class BlogGalleryListView(generics.ListCreateAPIView):
    serializer_class = BlogGallerySerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        qs = BlogGallery.objects.all().filter(user=user)
        return qs.order_by('-created')


class BlogGalleryDetailView(generics.RetrieveDestroyAPIView):
    queryset = BlogGallery.objects.all()
    serializer_class = BlogGallerySerializer
    permission_classes = (IsAuthenticated,)
