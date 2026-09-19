"""UI WinShit: spusteni .exe, historie, stav Protonu."""
import os
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

import i18n
import proton

_ = i18n.init()
APP_ID = "org.kuclab.WinShit"


class WinWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="WinShit")
        self.set_default_size(520, 420)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(box)
        header = Adw.HeaderBar()
        box.append(header)
        btn_open = Gtk.Button(label=_("Spustit .exe…"))
        btn_open.add_css_class("suggested-action")
        btn_open.connect("clicked", self.on_open)
        header.pack_end(btn_open)

        self.status_row = Adw.ActionRow(title=_("Proton-GE"))
        status_group = Adw.PreferencesGroup(title=_("Stav"))
        status_group.add(self.status_row)
        self.progress = Gtk.ProgressBar(show_text=True, visible=False)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(16)
        page.set_margin_end(16)
        page.set_margin_top(16)
        scroll = Gtk.ScrolledWindow(vexpand=True, child=page)
        box.append(scroll)
        page.append(status_group)
        page.append(self.progress)

        hist_group = Adw.PreferencesGroup(title=_("Naposledy spuštěné"))
        page.append(hist_group)
        self.hist_list = Gtk.ListBox()
        self.hist_list.add_css_class("boxed-list")
        hist_group.add(self.hist_list)

        self.refresh_history()
        threading.Thread(target=self.ensure_proton, daemon=True).start()

    def ensure_proton(self):
        if not proton.umu_available():
            GLib.idle_add(self.status_row.set_subtitle, _("Chybí umu-run (nainstaluje se s obrazem)."))
            return
        if proton.proton_ready():
            GLib.idle_add(self.status_row.set_subtitle, _("Připraveno"))
            return
        GLib.idle_add(self.status_row.set_subtitle, _("Stahuji Proton-GE (jen poprvé)…"))
        GLib.idle_add(self.progress.set_visible, True)
        err = proton.fetch_proton_ge(lambda f: GLib.idle_add(self.progress.set_fraction, f))
        GLib.idle_add(self.progress.set_visible, False)
        GLib.idle_add(
            self.status_row.set_subtitle, _("Připraveno") if not err else f"{_('Chyba')}: {err}"
        )

    def refresh_history(self):
        while (row := self.hist_list.get_row_at_index(0)) is not None:
            self.hist_list.remove(row)
        for item in reversed(proton.load_history()):
            row = Adw.ActionRow(title=item.get("name", "?"), subtitle=item.get("path", ""))
            btn = Gtk.Button(label=_("Spustit"), valign=Gtk.Align.CENTER)
            btn.connect("clicked", self.on_run_path, item["path"])
            row.add_suffix(btn)
            self.hist_list.append(row)

    def on_open(self, _btn):
        dlg = Gtk.FileDialog(title=_("Vyberte .exe"))
        exe_filter = Gtk.FileFilter(name="Windows (.exe, .msi)")
        exe_filter.add_pattern("*.exe")
        exe_filter.add_pattern("*.msi")
        dlg.set_filters(Gio.ListStore.new(Gtk.FileFilter))
        dlg.get_filters().append(exe_filter)
        dlg.open(self, None, self._open_done)

    def _open_done(self, dlg, result):
        try:
            f = dlg.open_finish(result)
        except Exception:
            return
        self.on_run_path(None, f.get_path())

    def on_run_path(self, _btn, path):
        if not os.path.exists(path):
            return
        if not proton.proton_ready():
            self.status_row.set_subtitle(_("Nejprve počkejte na stažení Protonu."))
            return
        try:
            proton.run_exe(path)
            proton.remember(path)
            self.refresh_history()
        except OSError as e:
            self.status_row.set_subtitle(f"{_('Chyba')}: {e}")


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        WinWindow(self).present()


def main():
    return App().run(sys.argv)
