#!/usr/bin/python
# ex:set fileencoding=utf-8:

from __future__ import unicode_literals

# from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from django.template.response import SimpleTemplateResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

import xml.etree.ElementTree as ET

from zipfile import ZipFile
from zipfile import ZIP_DEFLATED


try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from .serializers import TrackSerializer
from .parsers import Flight


@csrf_exempt
def parse_igc_file(request, template_name="paragliding/base.html"):

    if request.method == 'POST' and request.FILES:
        file_obj = request.FILES.get('track', None)

        flight = Flight(file_obj, file_obj.name)

        data = ET.tostring(flight.make_tree(
            ET.Element('kml', xmlns="http://earth.google.com/kml/2.2")
        ))

        inmemory_file = StringIO()
        with ZipFile(inmemory_file, 'w', ZIP_DEFLATED) as zipfile:
            zipfile.writestr(flight.name + '.kml', data)
        data = inmemory_file.getvalue()
        inmemory_file.close()

        response = HttpResponse(content_type="application/vnd.google-earth.kmz")
        response['Content-Disposition'] = "attachment; filename=%s" % flight.name + '.kmz'
        response.write(data)

        return response

    return SimpleTemplateResponse(template_name)


class TrackViewSet(viewsets.ViewSet):
    """
    """

    def get_serializer(self, *args, **kwargs):
        return TrackSerializer(*args, **kwargs)

    def list(self, request):
        return Response([])
