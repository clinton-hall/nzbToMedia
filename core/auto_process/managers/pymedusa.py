from .sickbeard import SickBeard


class PyMedusa(SickBeard):
    """PyMedusa class."""

    def __init__(self, config):
        super(PyMedusa, self).__init__(config)

    def configure():
        """Configure pymedusa with config options."""
