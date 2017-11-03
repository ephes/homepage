import logging

from rest_framework import serializers

from ..models import (
    BlogImage,
    BlogVideo,
    BlogGallery,
)

logger = logging.getLogger(__name__)


class BlogImageSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='api:image_detail')
    srcset = serializers.ReadOnlyField()
    thumbnail_src = serializers.ReadOnlyField()
    full_src = serializers.ReadOnlyField()

    class Meta:
        model = BlogImage
        fields = ('id', 'url', 'original', 'srcset', 'thumbnail_src', 'full_src')


class BlogVideoSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='api:video_detail')
    poster = serializers.ImageField(read_only=True, allow_empty_file=True)
    poster_thumbnail = serializers.ImageField(read_only=True, allow_empty_file=True)

    class Meta:
        model = BlogVideo
        fields = ('id', 'url', 'original', 'poster', 'poster_thumbnail')


class BlogGallerySerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='api:gallery_detail')
    images = serializers.PrimaryKeyRelatedField(
        many=True, queryset=BlogImage.objects.all())

    def create(self, validated_data):
        print(validated_data)
        user = self.context['request'].user
        gallery = BlogGallery.objects.create(user=user)
        for image in validated_data['images']:
            gallery.images.add(image)
        return gallery

    class Meta:
        model = BlogGallery
        fields = ('id', 'url', 'images')
