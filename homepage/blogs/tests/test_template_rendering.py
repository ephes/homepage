from django.template import Context, Template

import pytest


def test_template_render(test_templ):
    template = Template(test_templ)
    context = Context({})
    result = template.render(context)
    assert 'dolor' in result


@pytest.mark.django_db()
def test_blogimage_render(img_templ, blog_image):
    template = Template(img_templ)
    context = Context({})
    result = template.render(context)
    assert '<a href' in result
