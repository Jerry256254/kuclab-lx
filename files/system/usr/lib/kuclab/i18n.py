"""Sdileny gettext helper pro KucLab aplikace."""
import gettext
import locale
import os

DOMAIN = "kuclab"
_LOCALEDIR = "/usr/share/locale"


def init(app_name: str = DOMAIN):
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    gettext.bindtextdomain(DOMAIN, _LOCALEDIR)
    gettext.textdomain(DOMAIN)
    return gettext.gettext
