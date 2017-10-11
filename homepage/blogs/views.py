from __future__ import absolute_import

from django.views.generic import ListView
from django.views.generic import DetailView
from django.views.generic import CreateView

from django.contrib.syndication.views import Feed
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

from django.template import Context
from django.template import Template

from .forms import BlogPostForm

from .models import Blog
from .models import BlogPost


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
        blog_context = Context(
            {'javascript': javascript, 'blogpost': blogpost})
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
