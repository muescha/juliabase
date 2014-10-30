#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of JuliaBase, the samples database.
#
# Copyright © 2008–2014 Forschungszentrum Jülich, Germany,
#                       Marvin Goblet <m.goblet@fz-juelich.de>,
#                       Torsten Bronger <t.bronger@fz-juelich.de>
#
# You must not use, install, pass on, offer, sell, analyse, modify, or
# distribute this software without explicit permission of the copyright holder.
# If you have received a copy of this software without the explicit permission
# of the copyright holder, you must destroy it immediately and completely.


from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.conf import settings
from samples.models.common import ExternalOperator, Sample, SampleAlias, SampleSplit, SampleDeath, Result, \
    SampleSeries, Initials, UserDetails, Process, Clearance, SampleClaim, StatusMessage, Task
from samples.models.feeds import FeedNewSamples, FeedMovedSamples, FeedNewPhysicalProcess, FeedEditedPhysicalProcess, \
    FeedResult, FeedCopiedMySamples, FeedEditedSamples, FeedSampleSplit, FeedEditedSampleSeries, FeedNewSampleSeries, \
    FeedMovedSampleSeries, FeedChangedTopic, FeedStatusMessage


class SampleAdmin(admin.ModelAdmin):
    raw_id_fields = ("processes",)


class ClearanceAdmin(admin.ModelAdmin):
    raw_id_fields = ("processes",)


class TaskAdmin(admin.ModelAdmin):
    raw_id_fields = ("finished_process", "samples")


admin.site.register(ExternalOperator)
admin.site.register(Sample, SampleAdmin)
admin.site.register(SampleAlias)
admin.site.register(SampleSplit)
admin.site.register(SampleDeath)
admin.site.register(Result)
admin.site.register(SampleSeries)
admin.site.register(Initials)
admin.site.register(UserDetails)
admin.site.register(Process)
admin.site.register(Clearance, ClearanceAdmin)
admin.site.register(SampleClaim)
admin.site.register(StatusMessage)
admin.site.register(Task, TaskAdmin)

admin.site.register(FeedNewSamples)
admin.site.register(FeedMovedSamples)
admin.site.register(FeedNewPhysicalProcess)
admin.site.register(FeedEditedPhysicalProcess)
admin.site.register(FeedResult)
admin.site.register(FeedCopiedMySamples)
admin.site.register(FeedEditedSamples)
admin.site.register(FeedSampleSplit)
admin.site.register(FeedEditedSampleSeries)
admin.site.register(FeedNewSampleSeries)
admin.site.register(FeedMovedSampleSeries)
admin.site.register(FeedChangedTopic)
admin.site.register(FeedStatusMessage)


if settings.TESTING:
    from samples.models.test import TestPhysicalProcess
    admin.site.register(TestPhysicalProcess)
