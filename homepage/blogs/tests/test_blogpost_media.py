import pytest

@pytest.mark.django_db()
def test_blogpost_media_sync(blogpost, blog_image):
    print(blogpost.media_lookup)
    print(blog_image.pk)
    for mtype, media in blogpost.media_lookup.items():
        assert len(media) == 0

    # assert adding image to content adds link to m2m relation
    blogpost.content = '{{% blog_image {} %}}'.format(blog_image.pk)
    blogpost.save()
    assert blog_image.pk in blogpost.media_lookup['image']

    # assert removing image from content remvoves it from m2m relation, too
    blogpost.content = ''
    blogpost.save()
    print(blogpost.media_lookup)
    assert len(blogpost.images.all()) == 0
