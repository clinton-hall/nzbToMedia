"""
meta.py

Some useful metaclasses.
"""

from __future__ import unicode_literals

class LeafClassesMeta(type):
	"""
	A metaclass for classes that keeps track of all of them that
	aren't base classes.
	"""

	_leaf_classes = set()

	def __init__(cls, name, bases, attrs):
		if not hasattr(cls, '_leaf_classes'):
			cls._leaf_classes = set()
		leaf_classes = getattr(cls, '_leaf_classes')
		leaf_classes.add(cls)
		# remove any base classes
		leaf_classes -= set(bases)


class TagRegistered(type):
	"""
	As classes of this metaclass are created, they keep a registry in the
	base class of all classes by a class attribute, indicated by attr_name.
	"""
	attr_name = 'tag'

	def __init__(cls, name, bases, namespace):
		super(TagRegistered, cls).__init__(name, bases, namespace)
		if not hasattr(cls, '_registry'):
			cls._registry = {}
		meta = cls.__class__
		attr = getattr(cls, meta.attr_name, None)
		if attr:
			cls._registry[attr] = cls
