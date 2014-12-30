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


"""Signal handlers special to the institute.

Among other things, this module contains the signal listener for maintenance
work, which is called nightly.
"""

from __future__ import absolute_import, unicode_literals

import re
from django.db.models import signals
from django.dispatch import receiver
import django.contrib.auth.models
from django.utils.translation import ugettext as _
from jb_common.signals import maintain
import jb_common.utils.base as utils
from samples.models import Result, PhysicalProcess, Sample, SampleAlias
from institute import models as institute_app


@receiver(signals.pre_save)
def inform_process_supervisors(sender, instance, **kwargs):
    """Send an email to the supervisors of an apparatus when a user creates
    his or her first process of this apparatus.  If no supervisors are found,
    the administrators are emailed.
    """
    # FixMe: The following line is only necessary as long as
    # http://code.djangoproject.com/ticket/9318 is not fixed.  When it is
    # fixed, this function must be connected only with senders of
    # ``PhysicalProcess``.  If this is not possible because ``PhysicalProcess``
    # is abstract, this line must stay, and this function must be connected
    # with senders of ``Process`` only.
    if isinstance(instance, PhysicalProcess) and instance.finished:
        user = instance.operator
        process_class = instance.__class__
        if not process_class.objects.filter(operator=user).exists():
            try:
                permission = django.contrib.auth.models.Permission.objects.get(
                    codename="edit_permissions_for_{0}".format(utils.camel_case_to_underscores(process_class.__name__)))
            except django.contrib.auth.models.Permission.DoesNotExist:
                return
            recipients = list(django.contrib.auth.models.User.objects.filter(user_permissions=permission)) or \
                list(django.contrib.auth.models.User.objects.filter(is_staff=True).exclude(email=""))
            if recipients:
                _ = lambda x: x
                utils.send_email(_(u"{user_name} uses {apparatus}"),
                                 _(u"Dear supervisors of {apparatus_plural},\n\n{user_name} has "
                                   u"created their first {apparatus}.\n"), recipients,
                                 {"apparatus_plural": process_class._meta.verbose_name_plural,
                                  "apparatus": process_class._meta.verbose_name,
                                  "user_name": utils.get_really_full_name(user)})


@receiver(signals.post_save, sender=Sample)
def add_sample_details(sender, instance, created, **kwargs):
    """Create ``SampleDetails`` for every newly created sample.
    """
    if created:
        institute_app.SampleDetails.objects.get_or_create(sample=instance)


@receiver(signals.post_save)
def update_informal_layers(sender, instance, created, **kwargs):
    """Update the informal layers of all samples connected with the process
    that was recently changed.  Most of the work is done in the
    ``update_informal_layers`` method of the processes connected with each
    sample.  Their signature is::

        update_informal_layers(self, sample, process, informal_layers,
                               connected_informal_layers, modified_layers,
                               informal_layer)

    Here, ``sample`` is the to-be-updated sample, ``process`` is the process
    which triggered the update in the first place, ``informal_layers`` is a
    list with all so-far generated informal layers of the sample,
    ``connected_informal_layers`` is a list of the informal layers that are
    connected with the process (i.e., those layers that the previous runs of
    this method have generated), and ``modified_layers`` is a set containing
    all informal layers in ``informal_layers`` have have been modified (neither
    the added nor the deleted one, only the modified!).

    Finally, ``informal_layer`` is a factory function for new instances of
    ``InformalLayer``.  It already sets the ``sample_details`` and ``process``
    fields.

    ``informal_layers`` and ``modified_layers`` are to be extended in place by
    the method.

    This method must never modify the ``index`` field of an informal layer.
    Otherwise, newly generated informal layers may not be saved.  Moreover, it
    is not necessary to set ``verified = False`` for modified layers.
    """
    # FixMe: The following line is only necessary as long as
    # http://code.djangoproject.com/ticket/9318 is not fixed.  When it is
    # fixed, this function must be connected only with senders of
    # ``PhysicalProcess``.  If this is not possible because ``PhysicalProcess``
    # is abstract, this line must stay, and this function must be connected
    # with senders of ``Process`` only.
    #
    # FixMe: The following code doesn't seem to work if the index of an
    # existing informal layer is 0.  Either one must fix it here or prevent
    # such indices from happening.
    if isinstance(instance, PhysicalProcess) and instance.finished:
        def append_non_process_layers(consumed_layers=None):
            """Appends old informal layers not connected with a process to the
            new informal stack.  First, the `consumed_layers` are marked as
            “already added to the stack”, so that the non-process layers know
            which of them is next for being added to the stack.
            """
            if consumed_layers:
                for sub_layers in non_process_layers.values():
                    sub_layers -= consumed_layers
            while non_process_layers:
                next_layers = [layer for layer, sublayers in non_process_layers.items() if not sublayers]
                if not next_layers:
                    break
                assert len(next_layers) == 1
                next_layer = next_layers[0]
                informal_layers.append(next_layer)
                del non_process_layers[next_layer]
                one_removed = False
                for sub_layers in non_process_layers.values():
                    if next_layer in sub_layers:
                        sub_layers.remove(next_layer)
                        one_removed = True
                assert not non_process_layers or one_removed

        for sample in instance.samples.all():
            old_layers = list(sample.sample_details.informal_layers.all())
            non_process_layers = dict((layer, set(sub_layer for sub_layer in old_layers if sub_layer.index < layer.index))
                                      for layer in old_layers if not layer.process)
            informal_layers = []
            append_non_process_layers()
            modified_layers = set()
            for process in sample.processes.all():
                process = process.actual_instance
                if hasattr(process, "update_informal_layers"):
                    process_layers = [layer for layer in old_layers if layer.process == process]
                    process.update_informal_layers(
                        sample, instance, informal_layers, process_layers, modified_layers,
                        lambda **kwargs: institute_app.InformalLayer(sample_details=sample.sample_details,
                                                                        process=process, **kwargs))
                    append_non_process_layers(process_layers)
            informal_layers.extend(sorted(non_process_layers, key=lambda layer: layer.index))
            # This also removes layers whose processes have been withdrawn from
            # the sample.
            sample.sample_details.informal_layers.exclude(
                pk__in=set(layer.pk for layer in informal_layers if layer.pk)).delete()
            for layer in modified_layers:
                layer.verified = False
            for i, layer in enumerate(informal_layers):
                index = i + 1
                if layer.index != index or layer in modified_layers:
                    layer.index = index
                    layer.save(with_relations=False)


@receiver(maintain)
def clear_structuring_processes(sender, **kwargs):
    """Function to delete duplicated structuring processes.
    """
    for sample in Sample.objects.iterator():
        structurings = institute_app.Structuring.objects.filter(samples=sample).order_by("timestamp")
        if len(structurings) > 1:
            structurings[1].delete()