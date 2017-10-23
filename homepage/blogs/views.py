import logging

from collections import OrderedDict

from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
)

from django.views.decorators.http import require_http_methods

from django.contrib.syndication.views import Feed
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

from django.template import Context
from django.template import Template

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

from .forms import (
    BlogPostForm,
    BlogImageForm,
    BlogVideoForm,
)

from .models import (
    Blog,
    BlogPost,
    BlogImage,
    BlogVideo,
    BlogGallery,
)

logger = logging.getLogger(__name__)


class BlogsListView(ListView):
    model = Blog
    template_name = 'blogs/blog_list.html'
    context_object_name = 'blogs'


class BlogDetailView(DetailView):
    model = BlogPost
    template_name = 'blogs/blog_detail.html'
    context_object_name = 'blog'


class RenderPostMixin:
    def render_post(self, blogpost, javascript=True):
        content = '{}\n{}'.format(
            '{% load blogs_extras %}', blogpost.content)
        template = Template(content)
        blog_context = Context({
            'javascript': javascript,
            'blogpost': blogpost,
            'media': blogpost.media.all(),
        })
        blog_context.update(blogpost.media_lookup)
        blogpost.description = template.render(blog_context)


class AddRequestUserMixin:
    user_field_name = 'user'

    def form_valid(self, form):
        model = form.save(commit=False)
        setattr(model, self.user_field_name, self.request.user)
        return super().form_valid(form)


class PostsListView(RenderPostMixin, ListView):
    model = BlogPost
    template_name = 'blogs/blogpost_list.html'
    context_object_name = 'blogposts'
    paginate_by = 5

    def get_queryset(self):
        self.blog = get_object_or_404(Blog, slug=self.kwargs['slug'])
        queryset = BlogPost.objects.filter(blog=self.blog).order_by('-created')
        if not self.request.user.is_authenticated():
            queryset = queryset.filter(published=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['blog'] = self.blog
        for blogpost in context[self.context_object_name]:
            self.render_post(blogpost)
        return context


class LatestEntriesFeed(RenderPostMixin, Feed):
    def get_object(self, request, *args, **kwargs):
        self.object = get_object_or_404(Blog, slug=kwargs['slug'])

    def title(self):
        return self.object.title

    def description(self):
        return self.object.description

    def link(self):
        return reverse('blogs:blogpost-feed', kwargs={'slug': self.object.slug})

    def items(self):
        queryset = BlogPost.objects.filter(blog=self.object).order_by('-created')
        return queryset[:5]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        self.render_post(item, javascript=False)
        return item.description


class PostDetailView(RenderPostMixin, DetailView):
    model = BlogPost
    template_name = 'blogs/blogpost_detail.html'
    context_object_name = 'blogpost'
    slug_url_kwarg = 'slug'
    query_pk_and_slug = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blogpost = context[self.context_object_name]
        self.render_post(blogpost)
        return context


class PostCreateView(LoginRequiredMixin, AddRequestUserMixin, CreateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = 'blogs/blogpost_create.html'
    user_field_name = 'author'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if len(form.cleaned_data['slug']) == 0:
            self.object.slug = self.object.get_slug()
        blog = get_object_or_404(Blog, slug=self.kwargs['slug'])
        self.object.blog = blog
        return super().form_valid(form)


class FileUploadResponseMixin:
    def get_success_url(self):
        return None

    def form_valid(self, form):
        model = form.save(commit=False)
        respoonse = super().form_valid(form)
        return HttpResponse('{}'.format(model.pk))


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


# rest

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
