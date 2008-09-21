#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.shortcuts import render_to_response
from chantal.samples import models
from django import forms
from django.utils.translation import ugettext as _, ugettext_lazy
from chantal.samples.views.utils import check_permission
from chantal.samples.views import utils

class DepositionForm(forms.ModelForm):
    _ = ugettext_lazy
    class Meta:
        model = models.LargeAreaDeposition

class LayerForm(forms.ModelForm):
    _ = ugettext_lazy
    class Meta:
        model = models.LargeAreaLayer

class AddLayerForm(forms.Form):
    _ = ugettext_lazy
    number_of_layers_to_add = forms.IntegerField(label=_(u"Number of layers to be added"), min_value=0, required=False)
    def clean_number_of_layers_to_add(self):
        return utils.int_or_zero(self.cleaned_data["number_of_layers_to_add"])

class ChangeLayerForm(forms.Form):
    _ = ugettext_lazy
    duplicate_this_layer = forms.BooleanField(label=_(u"duplicate this layer"), required=False)
    remove_this_layer = forms.BooleanField(label=_(u"remove this layer"), required=False)

def forms_from_database(deposition):
    pass

def forms_from_post_data(post_data):
    post_data, number_of_layers, __ = utils.normalize_prefixes(post_data)
    layer_forms = [LayerForm(post_data, prefix=str(layer_index)) for layer_index in range(number_of_layers)]
    change_layer_forms = [ChangeLayerForm(post_data, prefix=str(change_layer_index))
                          for change_layer_index in range(number_of_layers)]
    return layer_forms, change_layer_forms

def change_structure(deposition_form, layer_forms, change_layer_forms, add_layer_form):
    layer_numbers = [layer_form.cleaned_data["number"] for layer_form in layer_forms if layer_form.is_valid()]
    if layer_numbers:
        next_layer_number = max(layer_numbers) + 1
    elif deposition_form.is_valid():
        match = re.match(ur"\d\dL-(\d+)", deposition_form.cleaned_data["number"])
        next_layer_number = int(match.group(1)) + 1 if match else 1
    else:
        next_layer_number = 1

    # Add layers
    if add_layer_form.is_valid():
        to_be_added_layers = add_layer_form.cleaned_data["number_of_layers_to_add"]
        old_number_of_layers = len(layer_forms)
        for layer_index in range(old_number_of_layers, old_number_of_layers + to_be_added_layers):
            layer_forms.append(LayerForm(initial={"number": next_layer_number}, prefix=str(layer_index)))
            next_layer_number += 1
            change_layer_forms.append(ChangeLayerForm(prefix=str(layer_index)))

    # Delete layers
    for layer_index in range(len(layer_forms)-1, -1, -1):
        if change_layer_forms[layer_index].is_valid() and \
                change_layer_forms[layer_index].cleaned_data["remove_this_layer"]:
            del layer_forms[layer_index], change_layer_forms[layer_index]

def is_all_valid(deposition_form, layer_forms, change_layer_forms, add_layer_form):
    all_valid = deposition_form.is_valid()
    all_valid = add_layer_form.is_valid() and all_valid
    all_valid = all([layer_form.is_valid() for layer_form in layer_forms]) and all_valid
    all_valid = all([change_layer_form.is_valid() for change_layer_form in change_layer_forms]) and all_valid
    return all_valid

@login_required
@check_permission("change_largeareadeposition")
def add(request):
    if request.method == "POST":
        deposition_form = DepositionForm(request.POST)
        add_layer_form = AddLayerForm(request.POST)
        layer_forms, change_layer_forms = forms_from_post_data(request.POST)
        all_valid = is_all_valid(deposition_form, layer_forms, change_layer_forms, add_layer_form)
        change_structure(deposition_form, layer_forms, change_layer_forms, add_layer_form)
    else:
        deposition_form = DepositionForm(initial={"number": utils.get_next_deposition_number("L-")})
        layer_forms, change_layer_forms = [], []
        add_layer_form = AddLayerForm()
    title = _(u"Add large-area deposition")
    return render_to_response("edit_large_area_deposition.html",
                              {"title": title, "deposition": deposition_form,
                               "layer_and_change_layer": zip(layer_forms, change_layer_forms),
                               "add_layer": add_layer_form},
                              context_instance=RequestContext(request))
