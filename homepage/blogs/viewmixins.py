import logging

from django.template import Context
from django.template import Template

from django.shortcuts import get_object_or_404

from .models import Blog

logger = logging.getLogger(__name__)


class RenderPostMixin:
    def render_post(self, blogpost, javascript=True):
        content = '{}\n{}'.format(
            '{% load blogs_extras %}', blogpost.content)
        template = Template(content)
        blog_context = Context({
            'javascript': javascript,
            'blogpost': blogpost,
        })
        blog_context.update(blogpost.media_lookup)
        blogpost.description = template.render(blog_context)


class AddRequestUserMixin:
    user_field_name = 'user'

    def form_valid(self, form):
        model = form.save(commit=False)
        setattr(model, self.user_field_name, self.request.user)
        return super().form_valid(form)


class PostChangeMixin:
    def form_valid(self, form):
        post = form.save(commit=False)
        if len(form.cleaned_data['slug']) == 0:
            post.slug = post.get_slug()
        blog = get_object_or_404(Blog, slug=self.blog_slug)
        post.blog = blog
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.info('form invalid: {}'.format(form.errors))
        return super().form_invalid(form)
