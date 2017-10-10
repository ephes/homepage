from django.template import Context, Template


def test_template_render(test_templ):
    template = Template(test_templ)
    context = Context({})
    result = template.render(context)

    assert 'dolor' in result
