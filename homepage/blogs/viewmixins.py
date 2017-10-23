import logging

from django.template import Context
from django.template import Template

logger = logging.getLogger(__name__)


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
