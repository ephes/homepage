import logging

from rest_framework import serializers

from .models import BlogImage

logger = logging.getLogger(__name__)


class BlogImageSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='api:image-detail')

    class Meta:
        model = BlogImage
        fields = ('id', 'url', 'original')
