import logging

from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
)

from django.http import HttpResponse

from django.contrib.syndication.views import Feed
from django.contrib.auth.mixins import LoginRequiredMixin

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

from django.template import Context
from django.template import Template

from .forms import BlogPostForm

from .models import (
    Blog,
    BlogPost,
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
        super().form_valid(form)
        return HttpResponse('{}'.format(model.pk))
