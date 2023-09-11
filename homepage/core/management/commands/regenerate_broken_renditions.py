import httpx

from django.core.management.base import BaseCommand

from cast.models import Blog, Post


def regenerate_renditions_for_image(image):
    """
    Get all renditions for an image and regenerate the ones where the file
    is not returning a 200.
    """
    new_renditions = []
    for rendition in image.renditions.all():
        r = httpx.head(rendition.url)
        if r.status_code == 200:
            continue
        # create new rendition - don't use get_rendition, because it will not create a file if
        # a rendition with the same filter already exists
        rendition_filter = rendition.filter
        rendition.delete()
        new_renditions.append(image.create_rendition(rendition_filter))
    return new_renditions


def regenerate_renditions_for_post(post):
    """
    Get all images for a post and regenerate the renditions for them.
    Return a list of the new renditions.
    """
    new_renditions = []
    for image in post.images.all():
        new_renditions.extend(regenerate_renditions_for_image(image))
    for gallery in post.galleries.all():
        for image in gallery.images.all():
            new_renditions.extend(regenerate_renditions_for_image(image))
    return new_renditions


class Command(BaseCommand):
    help = (
        "When the renditions were deleted from s3 - regenerate the ones "
        "that are missing. Provide slugs for blogs where renditions should be regenerated."
    )

    def add_arguments(self, parser):
        parser.add_argument("blog_slugs", nargs="+", type=str)

    def handle(self, *args, **options):
        new_renditions = []
        for slug in options["blog_slugs"]:
            blog = Blog.objects.get(slug=slug)
            print("Blog: ", slug, blog.title)
            post_queryset = Post.objects.all().descendant_of(blog).order_by("-visible_date")
            for post in post_queryset:
                new_renditions.extend(regenerate_renditions_for_post(post))
                print(post.pk, post)
                break
        print("generated renditions: ", len(new_renditions))

