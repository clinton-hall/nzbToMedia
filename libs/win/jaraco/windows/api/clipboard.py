import ctypes.wintypes

# Clipboard Formats
CF_TEXT = 1
CF_BITMAP = 2
CF_METAFILEPICT = 3
CF_SYLK = 4
CF_DIF = 5
CF_TIFF = 6
CF_OEMTEXT = 7
CF_DIB = 8
CF_PALETTE = 9
CF_PENDATA = 10
CF_RIFF = 11
CF_WAVE = 12
CF_UNICODETEXT = 13
CF_ENHMETAFILE = 14
CF_HDROP = 15
CF_LOCALE = 16
CF_DIBV5 = 17
CF_MAX = 18
CF_OWNERDISPLAY = 0x0080
CF_DSPTEXT = 0x0081
CF_DSPBITMAP = 0x0082
CF_DSPMETAFILEPICT = 0x0083
CF_DSPENHMETAFILE = 0x008E
CF_PRIVATEFIRST = 0x0200
CF_PRIVATELAST = 0x02FF
CF_GDIOBJFIRST = 0x0300
CF_GDIOBJLAST = 0x03FF

RegisterClipboardFormat = ctypes.windll.user32.RegisterClipboardFormatW
RegisterClipboardFormat.argtypes = (ctypes.wintypes.LPWSTR,)
RegisterClipboardFormat.restype = ctypes.wintypes.UINT
CF_HTML = RegisterClipboardFormat('HTML Format')

EnumClipboardFormats = ctypes.windll.user32.EnumClipboardFormats
EnumClipboardFormats.argtypes = (ctypes.wintypes.UINT,)
EnumClipboardFormats.restype = ctypes.wintypes.UINT

GetClipboardData = ctypes.windll.user32.GetClipboardData
GetClipboardData.argtypes = (ctypes.wintypes.UINT,)
GetClipboardData.restype = ctypes.wintypes.HANDLE

SetClipboardData = ctypes.windll.user32.SetClipboardData
SetClipboardData.argtypes = ctypes.wintypes.UINT, ctypes.wintypes.HANDLE
SetClipboardData.restype = ctypes.wintypes.HANDLE

OpenClipboard = ctypes.windll.user32.OpenClipboard
OpenClipboard.argtypes = (ctypes.wintypes.HANDLE,)
OpenClipboard.restype = ctypes.wintypes.BOOL

ctypes.windll.user32.CloseClipboard.restype = ctypes.wintypes.BOOL
