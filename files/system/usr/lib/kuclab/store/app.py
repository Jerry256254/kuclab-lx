"""UI obchodu: hledani, seznam, detail, instalace, repozitare."""
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

import backend
import i18n

_ = i18n.init()
APP_ID = "org.kuclab.Store"


class StoreWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("KucLab Store"))
        self.set_default_size(720, 520)
        self.backend = backend.Backend()

        self.nav = Adw.NavigationView()
        self.set_content(self.nav)

        main_page = Adw.NavigationPage(title=_("Obchod"))
        self.nav.add(main_page)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_page.set_child(box)

        header = Adw.HeaderBar()
        box.append(header)
        self.search = Gtk.SearchEntry(placeholder_text=_("Hledat aplikace…"), hexpand=True)
        self.search.connect("search-changed", lambda _e: self.do_search())
        header.set_title_widget(self.search)
        btn_remotes = Gtk.Button(icon_name="drive-multidisk-symbolic", tooltip_text=_("Zdroje aplikací"))
        btn_remotes.connect("clicked", lambda _b: RemotesDialog(self, self.backend).present())
        header.pack_end(btn_remotes)
        btn_refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text=_("Obnovit katalog"))
        btn_refresh.connect("clicked", self.on_refresh)
        header.pack_end(btn_refresh)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        box.append(scroll)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        scroll.set_child(self.list)

        self.status = Gtk.Label(label="", margin_start=12, margin_end=12, margin_top=6, margin_bottom=6)
        self.status.add_css_class("dim-label")
        box.append(self.status)
        self.do_search()

    def do_search(self):
        query = self.search.get_text()
        self.status.set_text(_("Hledám…"))

        def work():
            results = self.backend.search(query)
            GLib.idle_add(self.show_results, results)

        threading.Thread(target=work, daemon=True).start()

    def show_results(self, results):
        while (row := self.list.get_row_at_index(0)) is not None:
            self.list.remove(row)
        for app in results:
            row = Adw.ActionRow(title=app["name"], subtitle=app["summary"] or app["id"])
            btn = Gtk.Button(label=_("Odebrat") if app["installed"] else _("Instalovat"))
            if app["installed"]:
                btn.connect("clicked", self.on_remove, app)
            else:
                btn.add_css_class("suggested-action")
                btn.connect("clicked", self.on_install, app, btn)
            row.add_suffix(btn)
            self.list.append(row)
        self.status.set_text(_("Nalezeno: %d") % len(results))

    def on_install(self, _btn, app, btn):
        btn.set_sensitive(False)
        btn.set_label(_("Instaluji…"))
        self.backend.install(
            app["id"],
            on_progress=lambda frac, text: GLib.idle_add(btn.set_label, text),
            on_done=lambda ok, err: GLib.idle_add(self.install_done, ok, err, btn, app),
        )

    def install_done(self, ok, err, btn, app):
        if ok:
            btn.set_label(_("Odebrat"))
            btn.remove_css_class("suggested-action")
            btn.connect("clicked", self.on_remove, app)
        else:
            btn.set_label(_("Instalovat"))
            self.status.set_text(f"{_('Chyba')}: {err}")
        btn.set_sensitive(True)

    def on_remove(self, _btn, app):
        err = self.backend.remove(app["id"])
        self.status.set_text(_("Odebráno.") if not err else f"{_('Chyba')}: {err}")
        self.do_search()

    def on_refresh(self, _btn):
        self.status.set_text(_("Obnovuji katalog…"))

        def work():
            self.backend.refresh_blocking()
            GLib.idle_add(self.do_search)

        threading.Thread(target=work, daemon=True).start()


class RemotesDialog(Adw.PreferencesWindow):
    def __init__(self, parent, be: backend.Backend):
        super().__init__(transient_for=parent, title=_("Zdroje aplikací"))
        self.backend = be
        page = Adw.PreferencesPage()
        self.add(page)
        group = Adw.PreferencesGroup(title=_("Aktivní zdroje"))
        page.add(group)
        for name in be.remotes():
            group.add(Adw.ActionRow(title=name))
        group2 = Adw.PreferencesGroup(title=_("Přidat zdroj"))
        page.add(group2)
        for label, url in backend.EXTRA_REMOTES.items():
            row = Adw.ActionRow(title=label, subtitle=url)
            btn = Gtk.Button(label=_("Přidat"), valign=Gtk.Align.CENTER)
            btn.connect("clicked", self.on_add, label, url, btn)
            row.add_suffix(btn)
            group2.add(row)

    def on_add(self, _btn, label, url, btn):
        name = label.lower().replace(" ", "-")
        err = self.backend.add_remote(name, url)
        btn.set_sensitive(False)
        btn.set_label(_("Přidáno") if not err else _("Chyba"))


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        StoreWindow(self).present()


def main():
    return App().run(sys.argv)
