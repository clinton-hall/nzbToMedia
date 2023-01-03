from __future__ import annotations

from typing import Any

SICKCHILL_KEYS = ('proc_dir', 'failed', 'process_method', 'force', 'delete_on', 'force_next')
SICKCHILL_API_KEYS = ('path', 'proc_dir', 'failed', 'process_method', 'force', 'force_replace', 'return_data', 'type', 'delete', 'force_next', 'is_priority')

CONFIG: dict[str, dict[str, Any]] = {
    'SickChill': {key: None for key in SICKCHILL_KEYS},
    'SickChill-api': {
        **{key: None for key in SICKCHILL_API_KEYS},
        'cmd': 'postprocess',
    },
}
