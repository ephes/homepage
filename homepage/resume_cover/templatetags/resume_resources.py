from django import template

from homepage.resume_cover.resources import resources_for_slug

register = template.Library()


@register.simple_tag
def resume_resources(resume):
    return resources_for_slug(resume.slug)
