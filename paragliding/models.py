#!/usr/bin/python
# ex:set fileencoding=utf-8:

#from __future__ import unicode_literals

#from django.conf import settings
#from django.contrib.auth import get_user_model
#from django.db import models
#from django.utils.translation import ugettext_lazy as _
#from django.utils.encoding import python_2_unicode_compatible


#@python_2_unicode_compatible
#class Track(models.Model):
#    """
#    Track model
#    """
#    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=False, null=False, related_name="+", on_delete=models.CASCADE)
#    igc = models.FileField(
#        null=False,
#        blank=False,
#        verbose_name=_("IGC File"),
#    )
#
#    class Meta:
#        verbose_name = _('track')
#        verbose_name_plural = _('tracks')
#
#    def __str__(self):
#        return '%s' % self.igc
