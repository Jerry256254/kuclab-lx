"""UI Manageru: Prehled, Aplikace, Disky."""
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

import backend
import i18n

_ = i18n.init()
APP_ID = "org.kuclab.Manager"


class ManagerWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("KucLab Manager"))
        self.set_default_size(680, 520)
        view = Adw.ToolbarView()
        self.set_content(view)
        header = Adw.HeaderBar()
        view.add_top_bar(header)
        stack = Adw.ViewStack()
        view.set_content(stack)
        switcher = Adw.ViewSwitcherBar(stack=stack)
        view.add_bottom_bar(switcher)

        # Prehled
        overview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        overview.set_margin_start(16)
        overview.set_margin_end(16)
        overview.set_margin_top(16)
        scroll = Gtk.ScrolledWindow(vexpand=True, child=overview)
        stack.add_titled_with_icon(scroll, "overview", _("Přehled"), "computer-symbolic")
        self.info_group = Adw.PreferencesGroup(title=_("Systém"))
        overview.append(self.info_group)
        svc_group = Adw.PreferencesGroup(title=_("Běžící služby"))
        overview.append(svc_group)
        self.svc_list = Gtk.ListBox()
        self.svc_list.add_css_class("boxed-list")
        svc_group.add(self.svc_list)

        # Aplikace
        self.pkg_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.pkg_list.add_css_class("boxed-list")
        pkg_scroll = Gtk.ScrolledWindow(vexpand=True, child=self.pkg_list)
        stack.add_titled_with_icon(pkg_scroll, "packages", _("Aplikace"), "application-x-executable-symbolic")

        # Disky
        self.disk_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.disk_box.set_margin_start(16)
        self.disk_box.set_margin_end(16)
        self.disk_box.set_margin_top(16)
        disk_scroll = Gtk.ScrolledWindow(vexpand=True, child=self.disk_box)
        stack.add_titled_with_icon(disk_scroll, "disks", _("Disky"), "drive-harddisk-symbolic")

        threading.Thread(target=self.load_all, daemon=True).start()

    def load_all(self):
        info = backend.system_info()
        GLib.idle_add(self.show_info, info)
        svcs = backend.services()
        GLib.idle_add(self.show_services, svcs)
        pkgs = backend.flatpak_apps() + backend.layered_rpm()
        GLib.idle_add(self.show_packages, pkgs)
        GLib.idle_add(self.show_disks, backend.disk_usage(), backend.block_devices())

    def show_info(self, info):
        for key, label in (("os", _("Systém")), ("cpu", _("Procesor"))):
            if info.get(key):
                self.info_group.add(Adw.ActionRow(title=label, subtitle=str(info[key])[:80]))
        if info.get("ram_total_mb"):
            used = info["ram_total_mb"] - info.get("ram_avail_mb", 0)
            self.info_group.add(Adw.ActionRow(title=_("Paměť"), subtitle=f"{used} / {info['ram_total_mb']} MB"))

    def show_services(self, svcs):
        for name in svcs[:40]:
            row = Adw.ActionRow(title=name)
            btn = Gtk.Button(label=_("Zastavit"), valign=Gtk.Align.CENTER)
            btn.connect("clicked", self.on_service, name, "stop", row)
            row.add_suffix(btn)
            self.svc_list.append(row)

    def on_service(self, _btn, name, action, row):
        def work():
            err = backend.service_action(name, action)
            if not err:
                GLib.idle_add(self.svc_list.remove, row)

        threading.Thread(target=work, daemon=True).start()

    def show_packages(self, pkgs):
        while (row := self.pkg_list.get_row_at_index(0)) is not None:
            self.pkg_list.remove(row)
        for pkg in sorted(pkgs, key=lambda p: p["name"].lower()):
            row = Adw.ActionRow(title=pkg["name"], subtitle=f"{pkg['kind']} · {pkg['id']}")
            if pkg["protected"]:
                row.add_suffix(Gtk.Label(label=_("chráněno"), css_classes=["dim-label"], valign=Gtk.Align.CENTER))
            else:
                btn = Gtk.Button(label=_("Odebrat"), valign=Gtk.Align.CENTER)
                btn.add_css_class("destructive-action")
                btn.connect("clicked", self.on_remove_pkg, pkg, row)
                row.add_suffix(btn)
            self.pkg_list.append(row)

    def on_remove_pkg(self, _btn, pkg, row):
        dlg = Adw.MessageDialog(
            transient_for=self,
            heading=_("Odebrat aplikaci?"),
            body=f"{pkg['name']} ({pkg['id']})",
        )
        dlg.add_response("no", _("Zrušit"))
        dlg.add_response("yes", _("Odebrat"))
        dlg.set_response_appearance("yes", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", self._remove_confirmed, pkg, row, dlg)
        dlg.present()

    def _remove_confirmed(self, _dlg, resp, pkg, row, dlg):
        dlg.close()
        if resp != "yes":
            return

        def work():
            err = backend.remove_package(pkg["kind"], pkg["id"])
            if err in ("", "OK-REBOOT"):
                GLib.idle_add(self.pkg_list.remove, row)
            if err == "OK-REBOOT":
                GLib.idle_add(self.reboot_note)

        threading.Thread(target=work, daemon=True).start()

    def reboot_note(self):
        dlg = Adw.MessageDialog(
            transient_for=self,
            heading=_("Je potřeba restart"),
            body=_("Změna systémových balíčků se projeví po restartu."),
        )
        dlg.add_response("ok", _("Rozumím"))
        dlg.present()

    def show_disks(self, usage, _devices):
        group = Adw.PreferencesGroup(title=_("Využití"))
        self.disk_box.append(group)
        for row in usage:
            r = Adw.ActionRow(title=row["mount"], subtitle=f"{row['device']} · {row['used']} / {row['size']} ({row['pct']})")
            group.add(r)


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        ManagerWindow(self).present()


def main():
    return App().run(sys.argv)
