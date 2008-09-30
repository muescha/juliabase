#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ElementTree
import cPickle as pickle
import codecs

class Layer(object):
    def __init__(self):
        self.fields = {}

root = ElementTree.parse("/home/bronger/temp/large_area/content.xml")

topline_styles = []
bottomline_styles = []

for style in root.getiterator("{urn:oasis:names:tc:opendocument:xmlns:style:1.0}style"):
    property_ = style.find("{urn:oasis:names:tc:opendocument:xmlns:style:1.0}table-cell-properties")
    if property_ is not None:
        if property_.attrib.get("{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}border-top", "none") != "none":
            topline_styles.append(style.attrib["{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name"])
        if property_.attrib.get(
            "{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}border-bottom", "none") != "none":
            bottomline_styles.append(style.attrib["{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name"])

def text(root):
    if root.tag == "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}annotation":
        return u""
    current_text = root.text or u""
    for element in list(root):
        current_text += text(element)
    return current_text

class EmptyRowException(Exception):
    pass

layers = []
depositions = []

columns = ("number", "date", "layer_type", "station", "sih4", "h2", "__", "tmb", "ch4", "co2", "ph3", "power",
           "pressure", "temperature", "hf_frequency", "time", "dc_bias", "__", "__", "__", "__", "__", "__", "__", "__",
           "__", "__", "__", "__", "__", "__", "__", "__", "__", "__", "__", "electrode", "electrodes_distance",
           "comments")

for row in root.getiterator("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-row"):
    try:
        current_column = 0
        current_layer = Layer()
        last_layer_of_deposition = False
        for cell in row.getiterator("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-cell"):
            if current_column >= len(columns):
                break
            current_layer.fields[columns[current_column]] = text(cell)
            if current_column == 0 and not current_layer.fields["number"]:
                raise EmptyRowException
            if current_column == 38:
                stylename = cell.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}style-name")
                if stylename in topline_styles and layers:
                    depositions.append(layers)
                    layers = []
                if stylename in bottomline_styles:
                    last_layer_of_deposition = True
            current_column += int(
                cell.attrib.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-columns-repeated", 1))
        layers.append(current_layer)
        if last_layer_of_deposition:
            depositions.append(layers)
            layers = []
    except EmptyRowException:
        pass

# pickle.dump(depositions, open("large_area_depositions.pickle", "wb"))

# import sys
# sys.exit()

# depositions = pickle.load(open("large_area_depositions.pickle", "rb"))

del depositions[:3]

def datum2date(datum):
    return datum[6:10] + "-" + datum[3:5] + "-" + datum[0:2]

outfile = codecs.open("la_import.py", "w", encoding="utf-8")

print>>outfile, """#!/usr/bin/env python
# -*- coding: utf-8 -*-

from chantal_remote import *

login("bronger", "*******")

"""

started = False
last_date = None
for deposition in depositions:
    deposition_number = deposition[-1].fields["number"]
    if not deposition_number:
        continue
    comments = u"\\n".join(layer.fields["comments"] for layer in deposition)
    while comments[-4:] == "\\n\\n":
        comments = comments[:-2]
    while comments[:2] == "\\n":
        comments = comments[2:]
    comments = comments.replace('"', '\\"')
    date = datum2date(deposition[-1].fields["date"])
    if last_date is None or last_date != date:
        hour = 13
    else:
        hour += 1
    assert hour < 24
    last_date = date
    print>>outfile, u"""sample = new_samples(1, u"Großflächige-Labor", timestamp="%s 12:00:00")

deposition = LargeAreaDeposition(sample)
deposition.number = u"%s"
deposition.comments = u"%s"
deposition.timestamp = u'%s %02d:00:00'""" % (date, deposition_number, comments, date, hour)
    for layer in deposition:
        print>>outfile, "\nlayer = LargeAreaLayer(deposition)"
        for key, value in layer.fields.iteritems():
            if key != "__" and key != "comments":
                if key == "date":
                    value = datum2date(value)
                if key in ("sih4", "h2", "tmb", "ch4", "co2", "ph3", "power",
                           "pressure", "temperature", "hf_frequency", "time", "dc_bias", "electrodes_distance"):
                    value = value.replace(",", ".")
                    if key == "sih4" and value == "155-178.4":
                        value = "155"
                    if key == "dc_bias" and (value == "3...4" or value == "3-4"):
                        value = "3.5"
                    if key == "dc_bias" and value == "ca!!!":
                        value = ""
                    if value == "?":
                        value = "0"
                    if key in ("h2", "power") and not value:
                        value = "0"
                    if key == "time" and value == "ca. 10'":
                        value = "10"
                    if key == "time" and value == "?":
                        value = "0"
                if key == "number":
                    value = value[4:]
                if value:
                    print>>outfile, u"layer.%s = u\"%s\"" % (key, value.replace('"', '\\"'))
    print>>outfile, u"""
deposition_number = deposition.submit()

rename_after_deposition(deposition_number, {sample[0]: deposition_number})

"""

print>>outfile, "\n\nlogout()\n"