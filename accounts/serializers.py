"""Serializers powering the book categories API."""

from rest_framework import serializers


class CategorySerializer(serializers.Serializer):
    slug = serializers.SlugField()
    display_name = serializers.CharField()
    book_count_estimate = serializers.IntegerField(allow_null=True, required=False)


class BookSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    authors = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    description = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    categories = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    thumbnail = serializers.URLField(allow_blank=True, allow_null=True, required=False)
    info_url = serializers.URLField(allow_blank=True, allow_null=True, required=False)
    published_year = serializers.IntegerField(allow_null=True, required=False)
    source = serializers.CharField()
