# this is a namespace package
__import__('pkg_resources').declare_namespace(__name__)

try:
	# py2exe support (http://www.py2exe.org/index.cgi/ExeWithEggs)
	import modulefinder
	for p in __path__:
		modulefinder.AddPackagePath(__name__, p)
except ImportError:
	pass
