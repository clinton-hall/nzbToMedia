import ctypes.wintypes
BOOL = ctypes.wintypes.BOOL


class SHELLSTATE(ctypes.Structure):
	_fields_ = [
		('show_all_objects', BOOL, 1),
		('show_extensions', BOOL, 1),
		('no_confirm_recycle', BOOL, 1),
		('show_sys_files', BOOL, 1),
		('show_comp_color', BOOL, 1),
		('double_click_in_web_view', BOOL, 1),
		('desktop_HTML', BOOL, 1),
		('win95_classic', BOOL, 1),
		('dont_pretty_path', BOOL, 1),
		('show_attrib_col', BOOL, 1),
		('map_network_drive_button', BOOL, 1),
		('show_info_tip', BOOL, 1),
		('hide_icons', BOOL, 1),
		('web_view', BOOL, 1),
		('filter', BOOL, 1),
		('show_super_hidden', BOOL, 1),
		('no_net_crawling', BOOL, 1),
		('win95_unused', ctypes.wintypes.DWORD),
		('param_sort', ctypes.wintypes.LONG),
		('sort_direction', ctypes.c_int),
		('version', ctypes.wintypes.UINT),
		('not_used', ctypes.wintypes.UINT),
		('sep_process', BOOL, 1),
		('start_panel_on', BOOL, 1),
		('show_start_page', BOOL, 1),
		('auto_check_select', BOOL, 1),
		('icons_only', BOOL, 1),
		('show_type_overlay', BOOL, 1),
		('spare_flags', ctypes.wintypes.UINT, 13),
	]


SSF_SHOWALLOBJECTS = 0x00000001
"The fShowAllObjects member is being requested."

SSF_SHOWEXTENSIONS = 0x00000002
"The fShowExtensions member is being requested."

SSF_HIDDENFILEEXTS = 0x00000004
"Not used."

SSF_SERVERADMINUI = 0x00000004
"Not used."

SSF_SHOWCOMPCOLOR = 0x00000008
"The fShowCompColor member is being requested."

SSF_SORTCOLUMNS = 0x00000010
"The lParamSort and iSortDirection members are being requested."

SSF_SHOWSYSFILES = 0x00000020
"The fShowSysFiles member is being requested."

SSF_DOUBLECLICKINWEBVIEW = 0x00000080
"The fDoubleClickInWebView member is being requested."

SSF_SHOWATTRIBCOL = 0x00000100
"The fShowAttribCol member is being requested. (Windows Vista: Not used.)"

SSF_DESKTOPHTML = 0x00000200
"""
The fDesktopHTML member is being requested. Set is not available.
Instead, for versions of Microsoft Windows prior to Windows XP,
enable Desktop HTML by IActiveDesktop. The use of IActiveDesktop
for this purpose, however, is not recommended for Windows XP and
later versions of Windows, and is deprecated in Windows Vista.
"""

SSF_WIN95CLASSIC = 0x00000400
"The fWin95Classic member is being requested."

SSF_DONTPRETTYPATH = 0x00000800
"The fDontPrettyPath member is being requested."

SSF_MAPNETDRVBUTTON = 0x00001000
"The fMapNetDrvBtn member is being requested."

SSF_SHOWINFOTIP = 0x00002000
"The fShowInfoTip member is being requested."

SSF_HIDEICONS = 0x00004000
"The fHideIcons member is being requested."

SSF_NOCONFIRMRECYCLE = 0x00008000
"The fNoConfirmRecycle member is being requested."

SSF_FILTER = 0x00010000
"The fFilter member is being requested. (Windows Vista: Not used.)"

SSF_WEBVIEW = 0x00020000
"The fWebView member is being requested."

SSF_SHOWSUPERHIDDEN = 0x00040000
"The fShowSuperHidden member is being requested."

SSF_SEPPROCESS = 0x00080000
"The fSepProcess member is being requested."

SSF_NONETCRAWLING = 0x00100000
"Windows XP and later. The fNoNetCrawling member is being requested."

SSF_STARTPANELON = 0x00200000
"Windows XP and later. The fStartPanelOn member is being requested."

SSF_SHOWSTARTPAGE = 0x00400000
"Not used."

SSF_AUTOCHECKSELECT = 0x00800000
"Windows Vista and later. The fAutoCheckSelect member is being requested."

SSF_ICONSONLY = 0x01000000
"Windows Vista and later. The fIconsOnly member is being requested."

SSF_SHOWTYPEOVERLAY = 0x02000000
"Windows Vista and later. The fShowTypeOverlay member is being requested."


SHGetSetSettings = ctypes.windll.shell32.SHGetSetSettings
SHGetSetSettings.argtypes = [
	ctypes.POINTER(SHELLSTATE),
	ctypes.wintypes.DWORD,
	ctypes.wintypes.BOOL,  # get or set (True: set)
]
SHGetSetSettings.restype = None
