"""KucLab Store: rychly obchod pro Flatpak (AppStream metadata + Flatpak transakce)."""
import os
import threading

import gi

gi.require_version("Flatpak", "1.0")
try:
    gi.require_version("AppStream", "1.0")
    from gi.repository import AppStream
    HAVE_AS = True
except (ImportError, ValueError):
    HAVE_AS = False
from gi.repository import Flatpak, Gio

import i18n

_ = i18n.init()

EXTRA_REMOTES = {
    "Flathub Beta": "https://dl.flathub.org/beta-repo/flathub-beta.flatpakrepo",
    "GNOME Nightly": "https://nightly.gnome.org/gnome-nightly.flatpakrepo",
    "Fedora": "https://registry.fedoraproject.org/fedora.flatpakrepo",
}


class Backend:
    def __init__(self):
        self.sys = Flatpak.Installation.new_system()
        self.user = Flatpak.Installation.new_for_path(
            Gio.File.new_for_path(os.path.expanduser("~/.local/share/flatpak")), True
        )
        self.pool = None
        if HAVE_AS:
            self.pool = AppStream.Pool()
            self.pool.set_flags(AppStream.PoolFlags.LOAD_OS_CATALOG)
            self.pool.load()

    def refresh_blocking(self):
        for inst in (self.sys, self.user):
            try:
                inst.update_appstream_sync(None)
            except Exception:
                pass
        if self.pool:
            self.pool.refresh_cache(True)

    def search(self, query: str, limit=60) -> list:
        query = query.strip().lower()
        out = []
        if self.pool and HAVE_AS:
            for comp in self.pool.get_components():
                if comp.get_kind() != AppStream.ComponentKind.DESKTOP_APP:
                    continue
                bundle = comp.get_bundle(AppStream.BundleKind.FLATPAK)
                if bundle is None:
                    continue
                name = (comp.get_name() or "") or ""
                summary = (comp.get_summary() or "") or ""
                app_id = bundle.get_id() or ""
                if query and query not in name.lower() and query not in summary.lower() and query not in app_id.lower():
                    continue
                out.append(
                    {
                        "id": app_id,
                        "name": name or app_id,
                        "summary": summary,
                        "branch": bundle.get_branch() or "stable",
                        "runtime": "",
                        "installed": self.is_installed(app_id),
                    }
                )
                if len(out) >= limit:
                    break
        else:
            out = [{"id": i, "name": i, "summary": "", "branch": "stable", "installed": True} for i in self.installed_ids() if query in i.lower()]
        return out

    def installed_ids(self) -> set:
        ids = set()
        for inst in (self.sys, self.user):
            try:
                for ref in inst.list_installed_refs_by_kind(Flatpak.RefKind.APP, None):
                    ids.add(ref.get_name())
            except Exception:
                pass
        return ids

    def is_installed(self, app_id: str) -> bool:
        return app_id in self.installed_ids()

    def install(self, app_id: str, on_progress, on_done):
        def work():
            try:
                remote = "flathub"
                txn = Flatpak.Transaction.new_for_installation(self.sys, None)
                txn.add_install(remote, f"app/{app_id}/x86_64/stable", None)
                txn.connect("new-operation", lambda *a: on_progress(0.0, _("Příprava…")))
                txn.connect("progress-changed", lambda *a: on_progress(0.5, _("Stahování…")))
                txn.run(None)
                on_progress(1.0, _("Hotovo"))
                on_done(True, "")
            except Exception as e:  # noqa: BLE001
                on_done(False, str(e))

        threading.Thread(target=work, daemon=True).start()

    def remove(self, app_id: str) -> str:
        errors = []
        for inst in (self.sys, self.user):
            try:
                for ref in inst.list_installed_refs_by_kind(Flatpak.RefKind.APP, None):
                    if ref.get_name() == app_id:
                        inst.uninstall(ref, Flatpak.UninstallFlags.NONE, None)
            except Exception as e:  # noqa: BLE001
                errors.append(str(e))
        return "; ".join(errors)

    def remotes(self) -> list:
        out = []
        for inst in (self.sys, self.user):
            try:
                for r in inst.list_remotes(None):
                    out.append(r.get_name())
            except Exception:
                pass
        return sorted(set(out))

    def add_remote(self, name: str, url: str) -> str:
        try:
            builder = Flatpak.Remote.new(name)
            builder.set_url(url)
            self.sys.modify_remote(builder, None)
            return ""
        except Exception as e:  # noqa: BLE001
            return str(e)
