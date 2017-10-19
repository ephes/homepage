import logging

from collections import OrderedDict
from collections import defaultdict

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
from rest_framework.schemas import AutoSchema
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .serializers import BlogImageSerializer

from .forms import (
    BlogPostForm,
    BlogImageForm,
)

from .models import (
    Blog,
    BlogPost,
    BlogImage,
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
    def add_media_context(self, blogpost):
        media_context = defaultdict(dict)
        media = list(blogpost.media.all().prefetch_related('content_object'))
        for item in media:
            obj = item.content_object
            media_context[obj.blogpost_context_key][obj.pk] = obj
        return media_context

    def render_post(self, blogpost, javascript=True):
        content = '{}\n{}'.format(
            '{% load blogs_extras %}', blogpost.content)
        template = Template(content)
        blog_context = Context({
            'javascript': javascript,
            'blogpost': blogpost,
            'media': blogpost.media.all(),
        })
        blog_context.update(self.add_media_context(blogpost))
        blogpost.description = template.render(blog_context)


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


class PostCreateView(LoginRequiredMixin, CreateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = 'blogs/blogpost_create.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.slug = self.object.get_slug()
        self.object.author = self.request.user
        blog = get_object_or_404(Blog, slug=self.kwargs['slug'])
        self.object.blog = blog
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


@require_http_methods(['POST'])
def upload_file(request):
    '''Get Images via XmlHttpRequest'''
    form = BlogImageForm(request.POST, request.FILES)
    if form.is_valid() and request.user.is_authenticated():
        image = form.save(commit=False)
        image.user = request.user
        image.save()
    else:
        logger.warning(form.errors, request.user.is_authenticated())
    return HttpResponse('{}'.format(image.pk))


# rest

@api_view(['GET'])
def api_root(request):
    """
    Show API contents.
    If you add any object types, add them here!
    """
    return Response(OrderedDict((
        ('images',
         request.build_absolute_uri(reverse('api:image-list'))),
    )))


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 10000


class BlogImageListView(generics.ListCreateAPIView):
    schema = AutoSchema()
    queryset = BlogImage.objects.all()
    serializer_class = BlogImageSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = (IsAuthenticated,)


class BlogImageDetailView(generics.RetrieveDestroyAPIView):
    schema = AutoSchema()
    queryset = BlogImage.objects.all()
    serializer_class = BlogImageSerializer
    permission_classes = (IsAuthenticated,)
