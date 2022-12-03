import ctypes.wintypes

SystemParametersInfo = ctypes.windll.user32.SystemParametersInfoW
SystemParametersInfo.argtypes = (
    ctypes.wintypes.UINT,
    ctypes.wintypes.UINT,
    ctypes.c_void_p,
    ctypes.wintypes.UINT,
)

SPI_GETACTIVEWINDOWTRACKING = 0x1000
SPI_SETACTIVEWINDOWTRACKING = 0x1001
SPI_GETACTIVEWNDTRKTIMEOUT = 0x2002
SPI_SETACTIVEWNDTRKTIMEOUT = 0x2003
