VERSION = 'V4.3'

# Logging configuration
[loggers]
keys = root

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = NOTSET
handlers = console
qualname =

[handler_console]
class = StreamHandler
args = (sys.stdout,)
level = INFO
formatter = generic

[formatter_generic]
format = %(asctime)s|%(levelname)-7.7s %(message)s
datefmt = %H:%M:%S
