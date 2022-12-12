import ctypes.wintypes

from .error import handle_nonzero_success
from .api import filesystem


def DeviceIoControl(device, io_control_code, in_buffer, out_buffer, overlapped=None):
    if overlapped is not None:
        raise NotImplementedError("overlapped handles not yet supported")

    if isinstance(out_buffer, int):
        out_buffer = ctypes.create_string_buffer(out_buffer)

    in_buffer_size = len(in_buffer) if in_buffer is not None else 0
    out_buffer_size = len(out_buffer)
    assert isinstance(out_buffer, ctypes.Array)

    returned_bytes = ctypes.wintypes.DWORD()

    res = filesystem.DeviceIoControl(
        device,
        io_control_code,
        in_buffer,
        in_buffer_size,
        out_buffer,
        out_buffer_size,
        returned_bytes,
        overlapped,
    )

    handle_nonzero_success(res)
    handle_nonzero_success(returned_bytes)

    return out_buffer[: returned_bytes.value]
