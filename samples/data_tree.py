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


"""Module with classes that are needed to build nested representations of the
data contain in a certain model instance.  Such tree-like representations are
used e.g. for the CSV export of model instances.
"""

from __future__ import unicode_literals

class DataNode(object):
    """Class for a node in a data tree intended to hold instance data.

    :ivar name: name of this node; must be the same for node whose items carry
      the same semantics

    :ivar descriptive_name: name which is used if this node is a row node in
      the final tree, as a row description in the very first column.

    :ivar items: Key–value pairs with the actual data.  Again, for nodes with
      the same `name` (i.e. of the same *type*), this list must always have the
      same length and the sample key ordering.  Note that this is not a
      dictionary in order to preserve ordering.

    :ivar children: the child nodes of this node in the three; for example,
      they may be the samples of a sample series

    :type name: unicode
    :type descriptive_name: unicode
    :type items: list of (unicode, unicode)
    :type childen: list of `DataNode`
    """

    def __init__(self, instance, descriptive_name=""):
        """Class constructor.

        :Parameters:
          - `instance`: The model instance whose data is extracted, or the name
            that should be used for this node.  If you pass an instance, the
            name is the *type* of the instance, e.g. “6-chamber deposition” or
            “sample”.
          - `descriptive_name`: The “first column” name of the node.  It should
            be more concrete than just the type but it depends.  For samples
            for example, it is the sample's name.  By default, it is the type
            of the instance or the string you gave as ``instance``.

        :type instance: ``models.Model`` or unicode or str
        :type descriptive_name: unicode
        """
        if isinstance(instance, basestring):
            self.name = self.descriptive_name = instance
        else:
            self.name = unicode(instance._meta.verbose_name)
        self.descriptive_name = unicode(descriptive_name) or self.name
        self.items = []
        self.children = []

    def to_dict(self):
        """Converts the data which this node holds to a dictionary.  The
        dictionary maps the keys to the valus of each contained `DataItem`.
        Additionally, it maps node names of children to their dictionaries.

        If names of children collide with names of items – that's bad luck.
        The sample applies to colliding names of sibling nodes.  This simply
        must never happen.  You may call `find_unambiguous_names` before
        calling this method but this may make names very cumbersome.  So simply
        avoid it in the first place.

        :Return:
          data of this node in form of nested dictionaries

        :rtype: dict mapping unicode to dict or object
        """
        data = dict((item.key, item.value) for item in self.items)
        data.update((child.name, child.to_dict()) for child in self.children)
        return data

    def find_unambiguous_names(self, renaming_offset=1):
        """Make all names in the whole tree of this node instance
        unambiguous.  This is done by two means:

        1. If two sister nodes share the same name, a number like ``" #1"`` is
           appended.

        2. The names of the ancestor nodes are prepended, e.g. ``"6-chamber
           deposition, layer #2"``

        :Parameters:
          - `renaming_offset`: number of the nesting levels still to be stepped
            down before disambiguation of the node names takes place.

        :type renaming_offset: int
        """
        names = [child.name for child in self.children]
        for i, child in enumerate(self.children):
            if renaming_offset < 1:
                if names.count(child.name) > 1:
                    process_index = names[:i].count(child.name) + 1
                    if process_index > 1:
                        child.name += " #{0}".format(process_index)
                if renaming_offset < 0:
                    child.name = self.name + ", " + child.name
            child.find_unambiguous_names(renaming_offset - 1)

    def complete_items_in_children(self, key_sets=None, item_cache=None):
        """Assures that all decendents of this node that have the same node
        name also have the same item keys.  This is interesting for kinds of
        nodes which don't have a strict set of items.  An example are result
        processes: The user is completely free which items he gives them.  This
        irritates ``build_column_group_list``: It takes the *first* node of a
        certain ``name`` (for example ``"Nice result"``) and transforms its
        items to table columns.

        But what if the second ``"Nice result"`` for the same sample has other
        items?  This shouldn't happen certainly, but it will.  Here, we add
        the missing items (with empty strings as value).

        It must be called after `find_unambiguous_names` because the completion
        of item keys is only necessary within one column group, and the column
        groups base on the names created by ``find_unambiguous_names``.  In
        other words, if ``Nice result`` and ``Nice result #2`` don't share the
        same item keys, this is unimportant.  But if ``Nice result #2`` of two
        samples in the exported series didn't share the same item keys, this
        would result in a ``KeyError`` exception in
        ``cvs_export.Column.get_value``.

        This is not optimal for performance reasons.  But it is much easier
        than to train ``build_column_group_list`` to handle it.

        :Parameters:
          - `key_sets`: The item keys for all node names.  It is only used in
            the recursion.  If you call this method, you never give this
            parameter.
          - `item_cache`: The key names of the items for a given node.  Note
            that in contrast to `key_sets`, the keys of this are the nodes
            themselves rather than the disambiguated node names.  It is used
            for performance's sake.  If you call this method, you never give
            this parameter.

        :type key_sets: dict mapping unicode to set of (unicode, str)
        :type item_cache: dict mapping `DataNode` to set of (unicode, str)
        """
        if key_sets is None:
            item_cache = {}
            def collect_key_sets(node):
                """Collect all item keys of this node and its decentends.
                This is the first phase of the process.  It returns a mapping
                of node names (*not* node kinds) to item key sets.  We set both
                the ``key_sets`` and the ``item_cache`` here.
                """
                item_cache[node] = set((item.key, item.origin) for item in node.items)
                key_sets = {node.name: item_cache[node]}
                for child in node.children:
                    for name, key_set in collect_key_sets(child).items():
                        key_sets[name] = key_sets.setdefault(name, set()).union(key_set)
                return key_sets
            key_sets = collect_key_sets(self)
        missing_items = key_sets[self.name] - item_cache[self]
        for key, origin in missing_items:
            self.items.append(DataItem(key, "", origin))
        for child in self.children:
            child.complete_items_in_children(key_sets, item_cache)

    def __repr__(self):
        return repr(self.name)


class DataItem(object):
    """This class represents a key–value pair, holding the actual data in a
    `DataNode` tree.

    :ivar key: the key name of the data item

    :ivar value: the value of the data item

    :ivar origin: an optional name of the class from where this data item comes
      from.  Its necessity is not easy to explain.  The problem is that we have
      inheritance in the models, for example, a deposition is derived from
      `models.Process`.  When calling the ``get_data`` method of a deposition,
      it first calls the ``get_data`` method of ``models.Process``, which adds
      operator, timestamp, and comments to the items list.  However, the same
      is true for all other processes.

      But this means that e.g. the “timestamp” column ends up in different
      column groups when exporting the processes as rows in a table.  That's
      rubbish because it's actually always the same property.

      Thus, in order to preserve inheritance, such inherited attributes are
      called “shared columns” in Chantal's CSV export.  They are marked with a
      non-``None`` ``origin`` parameter which just contains a symbol for the
      model class, e.g. ``"process"`` for ``models.Process``.

    :type key: unicode
    :type value: object
    :type origin: unicode or ``NoneType``
    """

    def __init__(self, key, value, origin=None):
        """Class constructor.

        :Parameters:
          - `key`: the key name of the data item
          - `value`: the value of the data item
          - `origin`: an optional name of the class from where this data item
            comes from.

        :type key: unicode
        :type value: object
        :type origin: unicode or ``NoneType``
        """
        assert isinstance(key, basestring)
        self.key, self.value, self.origin = key, value, origin
