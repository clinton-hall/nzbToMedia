import logging
import logging.config
import os.path


def nzbtomedia_configure_logging(dirname):
  logFile = os.path.join(dirname, "postprocess.log")
  logging.config.fileConfig(os.path.join(dirname, "autoProcessMedia.cfg"))
  fileHandler = logging.FileHandler(logFile, encoding='utf-8', delay=True)
  fileHandler.formatter = logging.Formatter('%(asctime)s|%(levelname)-7.7s %(message)s', '%H:%M:%S')
  fileHandler.level = logging.DEBUG
  logging.getLogger().addHandler(fileHandler)
