from __future__ import annotations

from typing import Any

MEDUSA_KEYS = ('proc_dir', 'failed', 'process_method', 'force', 'delete_on', 'ignore_subs')
MEDUSA_API_KEYS = ('path', 'failed', 'process_method', 'force_replace', 'return_data', 'type', 'delete_files', 'is_priority')
MEDUSA_API_V2_KEYS = ('proc_dir', 'resource', 'failed', 'process_method', 'force', 'type', 'delete_on', 'is_priority')

CONFIG: dict[str, dict[str, Any]] = {
    'Medusa': {key: None for key in MEDUSA_KEYS},
    'Medusa-api': {
        **{key: None for key in MEDUSA_API_KEYS},
        'cmd': 'postprocess',
    },
    'Medusa-apiv2': {key: None for key in MEDUSA_API_V2_KEYS},
}
