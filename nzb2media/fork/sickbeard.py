from __future__ import annotations

from typing import Any

SICKBEARD_API_KEYS = ('path', 'failed', 'process_method', 'force_replace', 'return_data', 'type', 'delete', 'force_next')

CONFIG: dict[str, dict[str, Any]] = {
    'SickBeard-api': {
        **{key: None for key in SICKBEARD_API_KEYS},
        'cmd': 'postprocess',
    },
}
