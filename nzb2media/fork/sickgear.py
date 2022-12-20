from __future__ import annotations

from typing import Any

SICKGEAR_KEYS = ('dir', 'failed', 'process_method', 'force')
SICKGEAR_API_KEYS = ('path', 'process_method', 'force_replace', 'return_data', 'type', 'is_priority', 'failed')

CONFIG: dict[str, dict[str, Any]] = {
    'SickGear': {key: None for key in SICKGEAR_KEYS},
    'SickGear-api': {
        'cmd': 'sg.postprocess',
        **{key: None for key in SICKGEAR_API_KEYS},
    },
}
