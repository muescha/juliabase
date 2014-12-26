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


from __future__ import absolute_import, unicode_literals, division
from django.utils.six.moves import cStringIO as StringIO

import datetime, re
import numpy
from samples.views import shared_utils
from institute.views.samples import json_client
from samples import models


deposition_index_pattern = re.compile(r"\d{3,4}")

def get_next_deposition_number(letter):
    """Find a good next deposition number.  For example, if the last run was
    called “08B-045”, this routine yields “08B-046” (unless the new year has
    begun).

    :param letter: the indentifying letter of the deposition apparatus.  For
        example, it is ``"B"`` for the 6-chamber deposition.

    :type letter: str

    :return:
      A so-far unused deposition number for the current calendar year for the
      given deposition apparatus.
    """
    prefix = r"{0}{1}-".format(datetime.date.today().strftime("%y"), letter)
    prefix_length = len(prefix)
    pattern_string = r"^{0}[0-9]+".format(re.escape(prefix))
    deposition_numbers = \
        models.Deposition.objects.filter(number__regex=pattern_string).values_list("number", flat=True).iterator()
    numbers = [int(deposition_index_pattern.match(deposition_number[prefix_length:]).group())
               for deposition_number in deposition_numbers]
    next_number = max(numbers) + 1 if numbers else 1
    return prefix + "{0:03}".format(next_number)


def clean_up_after_merging(from_sample, to_sample):
    """Deletes the duplicate substrate process after merging two samples.

    :param from_sample: The sample which is merged into the other sample
    :param to_sample: The sample which should contain the processes from the
       other sample

    :type from_sample: `samples.models.Sample`
    :type to_sample: `samples.models.Sample`
    """
    substrates_to_sample = json_client.get_substrates(to_sample)
    substrate_from_sample = json_client.get_substrate(from_sample)
    if len(substrates_to_sample) == 2:
        substrates_to_sample.remove(substrate_from_sample)
        substrate_to_sample = substrates_to_sample[0]
        substrate_to_sample.timestamp = min(substrate_to_sample.timestamp, substrate_from_sample.timestamp)
        if substrate_from_sample.comments not in substrate_to_sample.comments:
            substrate_to_sample.comments += "\n\n{comments}".format(comments=substrate_from_sample.comments)
        substrate_to_sample.save()
        substrate_from_sample.samples.remove(to_sample)
        if substrate_from_sample.samples.count() == 1:
            substrate_from_sample.delete()


def read_solarsimulator_plot_file(filename, position):
    """Read a datafile from a solarsimulator measurement and return the content of
    the voltage column and the selected current column.

    :param filename: full path to the solarsimulator measurement data file
    :param position: the position of the cell the currents of which should be read.

    :type filename: str
    :type position: str

    :return:
      all voltages in Volt, then all currents in Ampere

    :rtype: list of float, list of float

    :raises PlotError: if something wents wrong with interpreting the file (I/O,
        unparseble data)
    """
    try:
        datafile_content = StringIO(open(filename).read())
    except IOError:
        raise shared_utils.PlotError("Data file could not be read.")
    for line in datafile_content:
        if line.startswith("# Positions:"):
            positions = line.partition(":")[2].split()
            break
    else:
        positions = []
    try:
        column = positions.index(position) + 1
    except ValueError:
        raise shared_utils.PlotError("Cell position not found in the datafile.")
    datafile_content.seek(0)
    try:
        return numpy.loadtxt(datafile_content, usecols=(0, column), unpack=True)
    except ValueError:
        raise shared_utils.PlotError("Data file format was invalid.")
