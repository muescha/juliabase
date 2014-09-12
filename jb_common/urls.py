#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of JuliaBase, the samples database.
#
# Copyright (C) 2010 Forschungszentrum Jülich, Germany,
#                    Marvin Goblet <m.goblet@fz-juelich.de>,
#                    Torsten Bronger <t.bronger@fz-juelich.de>
#
# You must not use, install, pass on, offer, sell, analyse, modify, or
# distribute this software without explicit permission of the copyright holder.
# If you have received a copy of this software without the explicit permission
# of the copyright holder, you must destroy it immediately and completely.


"""Mapping URL patterns to function calls.  This is the local URL dispatch of
the Django application “jb_common”, which provides core functionality and
core views for all JuliaBase apps.


:var urlpatterns: the actual mapping.  See the `Django documentation`_ for
  details.

.. _Django documentation:
    http://docs.djangoproject.com/en/dev/topics/http/urls/

"""

from __future__ import absolute_import, unicode_literals

from django.conf.urls import *
from django.conf import settings

urlpatterns = patterns("django.contrib.auth.views",
                       url(r"^change_password$", "password_change", {"template_name": "jb_common/change_password.html"},
                           name="password_change"),
                       url(r"^change_password/done/$", "password_change_done",
                        {"template_name": "jb_common/password_changed.html"}, name="password_change_done"),
                       url(r"^login$", "login", {"template_name": "jb_common/login.html"}, name="login"),
                       url(r"^logout$", "logout", {"template_name": "jb_common/logout.html"}, name="logout"),
                       )

urlpatterns += patterns("jb_common.views",
                        (r"^users/(?P<login_name>.+)", "show_user"),
                        (r"^markdown$", "markdown_sandbox"),
                        (r"^switch_language$", "switch_language"),
                        (r"^error_pages/(?P<hash_value>.+)", "show_error_page"),
                        )

urlpatterns += patterns("",
                        (r"^jsi18n/$", "django.views.i18n.javascript_catalog", {"packages": settings.JAVASCRIPT_I18N_APPS}),
                        )