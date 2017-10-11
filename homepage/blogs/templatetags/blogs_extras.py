from django import template
from django.utils.safestring import mark_safe

from ..models import BlogImage
from ..models import BlogVideo
from ..models import BlogGallery

register = template.Library()


@register.simple_tag
def blog_image(pk):
    image = BlogImage.objects.get(pk=pk)
    image_tag = (
        '<a href="{full}">'
        '  <img class="blog-image" src="{src}" srcset="{srcset}" sizes="100vw"></img>'
        '</a>'
    ).format(srcset=image.get_srcset(), src=image.img_xs.url, full=image.img_full.url)
    return mark_safe(image_tag)


@register.simple_tag
def blog_video(pk):
    video = BlogVideo.objects.get(pk=pk)
    video_tag = (
        '<video class="blog-video" preload="auto" controls>'
        '  <source src="{src}" type="video/mp4">'
        '</video>'
    ).format(src=video.original.url)
    return mark_safe(video_tag)


# blog_gallery tag

def get_modal_trigger(gallery_key, image, prev_img, next_img):
    srcset = image.get_srcset()
    prev_id = 'img-{}'.format(prev_img.pk) if prev_img is not None else 'false'
    next_id = 'img-{}'.format(next_img.pk) if next_img is not None else 'false'
    thumbnail_tag = (
        '<img id="img-{img_id}" class="gallery-thumbnail" src={src} '
        'srcset="{srcset}" data-prev="{prev}" data-next="{next}" '
        'data-full="{full}"></img>'
    ).format(img_id=image.pk, prev=prev_id, next=next_id, srcset=srcset,
             src=image.img_xs.url, full=image.img_full.url)
    return '''
        <a class="gallery-modal" data-toggle="modal" data-target="#galleryModal{key}">
            {thumbnail_tag}
        </a>
    '''.format(thumbnail_tag=thumbnail_tag, key=gallery_key)


def get_image_thumb(image):
    srcset = image.get_srcset()
    thumbnail_tag = (
        '<img class="gallery-thumbnail" src={src} '
        'srcset="{srcset}"</img>'
    ).format(src=image.img_xs.url, srcset=srcset)
    return '''
        <a href="{full}"">
            {thumbnail_tag}
        </a>
    '''.format(thumbnail_tag=thumbnail_tag, full=image.img_full.url)


def get_modal_tmpl():
    return '''
        {thumbs}
        <!-- Modal -->
        <div class="modal fade" id="galleryModal{key}" tabindex="-1" role="dialog"
             aria-labelledby="galleryModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg gallery-lg" role="document">
                <div class="modal-content gallery-content">
                    <div class="modal-header gallery-header">
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body gallery-body">
                        <a href=""><img class="modal-image blog-image" src="" srcset="" sizes="100vw"></img></a>
                    </div>
                    <div class="modal-footer gallery-footer">
                        </div>
                    </div>
            </div>
        </div>
    '''


def blog_gallery_with_javascript(pk, blogpost):
    image_thumbs = ['<!-- Button trigger modal -->']

    gallery = BlogGallery.objects.get(pk=pk)
    gallery_key = '{}_{}'.format(blogpost.pk, pk)
    prev_img, next_img = None, None
    images = list(gallery.images.all())
    for num, image in enumerate(images, 1):
        if num < len(images):
            next_img = images[num]
        else:
            next_img = None
        image_thumbs.append(get_modal_trigger(gallery_key, image, prev_img, next_img))
        prev_img = image
    thumbs = '\n'.join(image_thumbs)
    return get_modal_tmpl().format(thumbs=thumbs, key=gallery_key)


def blog_gallery_without_javascript(pk):
    image_thumbs = []
    gallery = BlogGallery.objects.get(pk=pk)
    for image in gallery.images.all():
        image_thumbs.append(get_image_thumb(image))
    return '\n'.join(image_thumbs)


@register.simple_tag(takes_context=True)
def blog_gallery(context, pk):
    use_javascript = context.get('javascript', True)
    blogpost = context['blogpost']
    if use_javascript:
        gallery_html = blog_gallery_with_javascript(pk, blogpost)
    else:
        gallery_html = blog_gallery_without_javascript(pk)

    return mark_safe(gallery_html)
