from .api import shell


def get_recycle_bin_confirm():
    settings = shell.SHELLSTATE()
    shell.SHGetSetSettings(settings, shell.SSF_NOCONFIRMRECYCLE, False)
    return not settings.no_confirm_recycle


def set_recycle_bin_confirm(confirm=False):
    settings = shell.SHELLSTATE()
    settings.no_confirm_recycle = not confirm
    shell.SHGetSetSettings(settings, shell.SSF_NOCONFIRMRECYCLE, True)
    # cross fingers and hope it worked
