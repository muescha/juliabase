#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Chantal, the samples database.
#
# Copyright (C) 2010 Forschungszentrum Jülich, Germany,
#                    Marvin Goblet <m.goblet@fz-juelich.de>,
#                    Torsten Bronger <t.bronger@fz-juelich.de>
#
# You must not use, install, pass on, offer, sell, analyse, modify, or
# distribute this software without explicit permission of the copyright holder.
# If you have received a copy of this software without the explicit permission
# of the copyright holder, you must destroy it immediately and completely.


u"""View for editing the “My Layers” structure.  See
``models.UserDetails.my_layers`` for the syntax of the “My Layers” field.
"""

from __future__ import absolute_import

import re
from django.utils.translation import ugettext as _, ugettext_lazy
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.forms.util import ValidationError
import django.contrib.auth.models
from chantal_common.utils import append_error
from samples import models, permissions
from samples.views import utils


class MyLayerForm(forms.Form):
    u"""Form for editing the “My Layers” structure.
    """
    _ = ugettext_lazy
    nickname = forms.CharField(label=_(u"Nickname"))
    deposition_and_layer = forms.CharField(label=_(u"Layer identifier"),
                                           help_text=_(u"in the form \"deposition number\"-\"layer number\""))
    delete = forms.BooleanField(label=_(u"Delete"), required=False)

    def clean_deposition_and_layer(self):
        u"""Convert the notation ``<deposition number>-<layer number>`` to
        ``<deposition ID>-<layer number>``.  Additionaly, do some validity
        tests.
        """
        if "-" not in self.cleaned_data["deposition_and_layer"]:
            raise ValidationError(_(u"Deposition and layer number must be separated by \"-\"."))
        deposition_number, layer_number = self.cleaned_data["deposition_and_layer"].rsplit("-", 1)
        try:
            deposition = models.Deposition.objects.get(number=deposition_number).actual_instance
        except models.Deposition.DoesNotExist:
            raise ValidationError(_(u"Deposition number doesn't exist."))
        try:
            layer_number = int(layer_number)
        except ValueError:
            raise ValidationError(_(u"Layer number isn't a number."))
        # FixMe: Handle the case when there is no "layers" attribute
        if not deposition.layers.filter(number=layer_number).exists():
            raise ValidationError(_(u"This layer does not exist in this deposition."))
        return u"{0}-{1}".format(deposition.id, layer_number)


layer_item_pattern = re.compile(ur"\s*(?P<nickname>.+?)\s*:\s*(?P<raw_layer_identifier>.+?)\s*(?:,\s*|\Z)")
def forms_from_database(user):
    u"""Generate the “My Layers” forms for the current user.  Convert the
    notation ``<deposition ID>-<layer number>`` of the database to
    ``<deposition number>-<layer number>``.

    :Parameters:
      - `user`: the current user

    :type user: ``django.contrib.auth.models.User``

    :Return:
      the “My Layers” forms

    :rtype: list of `MyLayerForm`
    """
    my_layer_forms = []
    my_layers_serialized = user.samples_user_details.my_layers
    while my_layers_serialized:
        next_match = layer_item_pattern.match(my_layers_serialized)
        nickname, raw_layer_identifier = next_match.group("nickname"), next_match.group("raw_layer_identifier")
        process_id, layer_number = raw_layer_identifier.rsplit("-", 1)
        process_id, layer_number = int(process_id), int(layer_number)
        deposition_number = models.Process.objects.get(pk=process_id).actual_instance.number
        deposition_and_layer = u"{0}-{1}".format(deposition_number, layer_number)
        my_layer_forms.append(MyLayerForm(initial={"nickname": nickname, "deposition_and_layer": deposition_and_layer},
                                          prefix=str(len(my_layer_forms))))
        my_layers_serialized = my_layers_serialized[next_match.end():]
    return my_layer_forms


def forms_from_post_data(post_data):
    u"""Interpret the POST data and create bound forms for with the “My Layers”
    from it.  This also includes the functionality of the ``change_structure``
    function found in other modules.

    :Parameters:
      - `post_data`: the result from ``request.POST``

    :type post_data: ``QueryDict``

    :Return:
      list of “My Layers” forms, whether the structure was changed (i.e. a
      layer was deleted or added)

    :rtype: list of `MyLayerForm`, bool
    """
    my_layer_forms = []
    structure_changed = False
    index = 0
    while True:
        if "{0}-nickname".format(index) not in post_data:
            break
        if "{0}-delete".format(index) in post_data:
            structure_changed = True
        else:
            my_layer_forms.append(MyLayerForm(post_data, prefix=str(index)))
        index += 1
    if my_layer_forms and not post_data["{0}-nickname".format(index - 1)]:
        del my_layer_forms[-1]
    else:
        structure_changed = True
    return my_layer_forms, structure_changed


def is_referentially_valid(my_layer_forms):
    u"""Test whether no nickname occurs twice.

    :Return:
      whether all nicknames are unique

    :rtype: bool
    """
    referentially_valid = True
    nicknames = set()
    for my_layer_form in my_layer_forms:
        if my_layer_form.is_valid():
            nickname = my_layer_form.cleaned_data["nickname"]
            if nickname in nicknames:
                append_error(my_layer_form, _(u"Nickname is already given."))
                referentially_valid = False
            else:
                nicknames.add(nickname)
    return referentially_valid


def save_to_database(my_layer_forms, user):
    u"""Save the new “My Layers” into the database.
    """
    user_details = user.samples_user_details
    user_details.my_layers = \
        u", ".join(["{0}: {1}".format(form.cleaned_data["nickname"], form.cleaned_data["deposition_and_layer"])
                    for form in my_layer_forms])
    user_details.save()


@login_required
def edit(request, login_name):
    u"""View for editing the “My Layers”.

    :Parameters:
      - `request`: the current HTTP Request object
      - `login_name`: the login name of the user whose “My Layers” should be
        changed

    :type request: ``HttpRequest``
    :type login_name: unicode

    :Returns:
      the HTTP response object

    :rtype: ``HttpResponse``
    """
    user = get_object_or_404(django.contrib.auth.models.User, username=login_name)
    if not request.user.is_staff and request.user != user:
        raise permissions.PermissionError(request.user, _(u"You can't access the “My Layers” section of another user."))
    if request.method == "POST":
        my_layer_forms, structure_changed = forms_from_post_data(request.POST)
        all_valid = all([my_layer_form.is_valid() for my_layer_form in my_layer_forms])
        referentially_valid = is_referentially_valid(my_layer_forms)
        if all_valid and referentially_valid and not structure_changed:
            save_to_database(my_layer_forms, user)
            return utils.successful_response(request)
    else:
        my_layer_forms = forms_from_database(user)
    my_layer_forms.append(MyLayerForm(prefix=str(len(my_layer_forms))))
    return render_to_response("samples/edit_my_layers.html", {"title": _(u"My Layers"), "my_layers": my_layer_forms},
                              context_instance=RequestContext(request))

