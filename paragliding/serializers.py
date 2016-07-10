#!/usr/bin/python
# ex:set fileencoding=utf-8:

from __future__ import unicode_literals

from rest_framework import serializers


class TrackSerializer(serializers.Serializer):
    track = serializers.FileField(use_url=False)
