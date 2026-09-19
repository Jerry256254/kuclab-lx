"""Popup chat agenta (GTK4 + libadwaita) vcetne nastaveni a hlasu."""
import os
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

import agent as agent_mod
import config
import daemon as daemon_mod
import i18n
import policy as policy_mod
import tools
import voice

_ = i18n.init()

TOOL_LABELS = {
    "system_info": _("Info o systému"),
    "list_dir": _("Výpis adresáře"),
    "read_file": _("Čtení souborů"),
    "write_file": _("Zápis souborů"),
    "run_command": _("Spouštění příkazů"),
    "open_app": _("Otevírání aplikací"),
    "install_flatpak": _("Instalace aplikací"),
    "remove_flatpak": _("Odebírání aplikací"),
    "web_get": _("Stahování z webu"),
}

MODE_LABELS = {policy_mod.ALLOW: _("Povolit"), policy_mod.ASK: _("Zeptat se"), policy_mod.DENY: _("Zakázat")}


class ChatWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("KucLab Agent"))
        self.set_default_size(420, 560)
        self.history: list[dict] = []
        self.busy = False

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.box)

        header = Adw.HeaderBar()
        self.box.append(header)
        self.status = Gtk.Label(label=_("Připraven"))
        self.status.add_css_class("dim-label")
        header.set_title_widget(self.status)

        btn_voice = Gtk.Button(icon_name="audio-input-microphone-symbolic", tooltip_text=_("Hlasový vstup"))
        btn_voice.connect("clicked", self.on_voice_input)
        header.pack_start(btn_voice)
        btn_settings = Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text=_("Nastavení"))
        btn_settings.connect("clicked", lambda _b: SettingsWindow(self).present())
        header.pack_end(btn_settings)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        self.box.append(scroll)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        scroll.set_child(self.list)

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_row.set_margin_start(12)
        input_row.set_margin_end(12)
        input_row.set_margin_top(8)
        input_row.set_margin_bottom(12)
        self.box.append(input_row)
        self.entry = Gtk.Entry(placeholder_text=_("Napište dotaz…"), hexpand=True)
        self.entry.connect("activate", lambda _e: self.send())
        input_row.append(self.entry)
        btn_send = Gtk.Button(icon_name="paper-plane-symbolic", tooltip_text=_("Odeslat"))
        btn_send.add_css_class("suggested-action")
        btn_send.connect("clicked", lambda _b: self.send())
        input_row.append(btn_send)

    def bubble(self, text: str, me: bool):
        label = Gtk.Label(
            label=GLib.markup_escape_text(text),
            use_markup=True,
            wrap=True,
            xalign=1.0 if me else 0.0,
            selectable=True,
        )
        row = Gtk.ListBoxRow(child=label, activatable=False)
        row.set_margin_start(48 if me else 6)
        row.set_margin_end(6 if me else 48)
        self.list.append(row)
        return label

    def send(self, text: str | None = None):
        text = (text if text is not None else self.entry.get_text()).strip()
        if not text or self.busy:
            return
        self.entry.set_text("")
        self.bubble(text, me=True)
        self.history.append({"role": "user", "content": text})
        self.busy = True
        self.status.set_text(_("Přemýšlím…"))
        label = self.bubble("", me=False)
        buf: list[str] = []

        def on_token(tok):
            buf.append(tok)
            GLib.idle_add(label.set_markup, GLib.markup_escape_text("".join(buf)))

        def confirm(tool, args):
            done = threading.Event()
            result = {"ok": False}

            def ask_ui():
                dlg = Adw.MessageDialog(
                    transient_for=self,
                    heading=_("Agent chce použít nástroj"),
                    body=f"{TOOL_LABELS.get(tool, tool)}\n{args}",
                )
                dlg.add_response("no", _("Zamítnout"))
                dlg.add_response("yes", _("Povolit"))
                dlg.set_response_appearance("yes", Adw.ResponseAppearance.SUGGESTED)
                dlg.connect("response", lambda _d, r: (result.update(ok=r == "yes"), done.set(), _d.close()))
                dlg.present()

            GLib.idle_add(ask_ui)
            done.wait(timeout=300)
            return result["ok"]

        def work():
            try:
                try:
                    client = daemon_mod.Client()
                    try:
                        result = client.ask(self.history, on_token=on_token, confirm=confirm)
                    finally:
                        client.close()
                except OSError:
                    ag = agent_mod.Agent(config.load())
                    result = ag.ask(self.history, on_token=on_token, confirm=confirm)
                final = result["text"] or _("Hotovo.")
                self.history.append({"role": "assistant", "content": final})
                GLib.idle_add(label.set_markup, GLib.markup_escape_text(final))
                if result.get("actions"):
                    summary = "\n".join(
                        f"• {TOOL_LABELS.get(a['tool'], a['tool'])}: "
                        + (_("provedeno") if a["allowed"] else _("zamítnuto"))
                        for a in result["actions"]
                    )
                    GLib.idle_add(self.bubble, summary, False)
                GLib.idle_add(self._done, True)
            except Exception as e:  # noqa: BLE001 - chyba se ukaze uzivateli
                GLib.idle_add(label.set_text, f"{_('Chyba')}: {e}")
                GLib.idle_add(self._done, False)

        threading.Thread(target=work, daemon=True).start()

    def _done(self, _ok):
        self.busy = False
        self.status.set_text(_("Připraven"))

    def on_voice_input(self, _btn):
        # prvni klik = start nahravani, druhy klik = stop a prepis
        if getattr(self, "rec_proc", None):
            proc, self.rec_proc = self.rec_proc, None
            voice.stop_recording(proc)
            self.status.set_text(_("Přepisuji…"))

            def work():
                import tempfile

                cfg = config.load()
                lang = cfg.get("voice_lang", "cs")
                path = os.path.join(tempfile.gettempdir(), "kuclab-voice.wav")
                try:
                    text = voice.transcribe(path, lang)
                except Exception as e:  # noqa: BLE001
                    text = ""
                    GLib.idle_add(self.bubble, f"{_('Chyba přepisu')}: {e}", False)
                if text:
                    GLib.idle_add(self._voice_text, text, lang)
                else:
                    GLib.idle_add(self.bubble, _("Nerozuměl jsem, zkuste to prosím znovu."), False)
                GLib.idle_add(self._done, True)

            threading.Thread(target=work, daemon=True).start()
            return
        if self.busy:
            return
        stt_ok, _tts_ok = voice.available()
        if not stt_ok:
            self.bubble(_("Hlasové nástroje nejsou nainstalované."), me=False)
            return
        import tempfile

        path = os.path.join(tempfile.gettempdir(), "kuclab-voice.wav")
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            pass
        proc = voice.start_recording(path)
        if not proc:
            self.bubble(_("Nahrávání se nezdařilo."), me=False)
            return
        self.rec_proc = proc
        self.busy = True
        self.status.set_text(_("Nahrávám… klikněte znovu pro ukončení"))

    def _voice_text(self, text, lang):
        if config.load().get("voice_enabled"):
            threading.Thread(target=voice.speak, args=(text, lang), daemon=True).start()
        self.send(text)


class SettingsWindow(Adw.PreferencesWindow):
    def __init__(self, parent):
        super().__init__(transient_for=parent, title=_("Nastavení agenta"))
        self.cfg = config.load()

        page = Adw.PreferencesPage(title=_("Model"), icon_name="brain-symbolic")
        self.add(page)
        group = Adw.PreferencesGroup(title=_("Poskytovatel"))
        page.add(group)

        self.provider = Adw.ComboRow(
            title=_("Běh modelu"),
            model=Gtk.StringList.new([_("Lokální (Ollama)"), _("Vzdálené API (OpenAI-kompatibilní)")]),
            selected=0 if self.cfg.get("provider") == "ollama" else 1,
        )
        self.provider.connect("notify::selected", self.on_provider)
        group.add(self.provider)

        self.ollama_model = Adw.EntryRow(title=_("Lokální model"))
        self.ollama_model.set_text(self.cfg.get("ollama_model", ""))
        self.ollama_model.connect("changed", lambda _e: self.save_field("ollama_model", self.ollama_model.get_text()))
        group.add(self.ollama_model)

        self.api_base = Adw.EntryRow(title=_("API adresa"))
        self.api_base.set_text(self.cfg.get("openai_base_url", ""))
        self.api_base.connect("changed", lambda _e: self.save_field("openai_base_url", self.api_base.get_text()))
        group.add(self.api_base)

        self.api_key = Adw.PasswordEntryRow(title=_("API klíč"))
        self.api_key.set_text(self.cfg.get("openai_api_key", ""))
        self.api_key.connect("changed", lambda _e: self.save_field("openai_api_key", self.api_key.get_text()))
        group.add(self.api_key)

        self.api_model = Adw.EntryRow(title=_("API model"))
        self.api_model.set_text(self.cfg.get("openai_model", ""))
        self.api_model.connect("changed", lambda _e: self.save_field("openai_model", self.api_model.get_text()))
        group.add(self.api_model)

        page2 = Adw.PreferencesPage(title=_("Oprávnění"), icon_name="emblem-readonly-symbolic")
        self.add(page2)
        group2 = Adw.PreferencesGroup(
            title=_("Co smí agent dělat"),
            description=_("Profily: konzervativní = vše zakázáno, vyvážený = ptát se, plná důvěra = vše povoleno."),
        )
        page2.add(group2)
        profiles = Gtk.StringList.new([_("Konzervativní"), _("Vyvážený"), _("Plná důvěra")])
        self.profile = Adw.ComboRow(title=_("Profil"), model=profiles, selected=1)
        self.profile.connect("notify::selected", self.on_profile)
        group2.add(self.profile)

        self.policy = policy_mod.load(tools.tool_names())
        self.tool_rows: dict[str, Adw.ComboRow] = {}
        modes = Gtk.StringList.new([MODE_LABELS[policy_mod.ALLOW], MODE_LABELS[policy_mod.ASK], MODE_LABELS[policy_mod.DENY]])
        order = [policy_mod.ALLOW, policy_mod.ASK, policy_mod.DENY]
        for name in tools.tool_names():
            row = Adw.ComboRow(title=TOOL_LABELS.get(name, name), model=modes, selected=order.index(self.policy.get(name, policy_mod.ASK)))
            row.connect("notify::selected", self.on_tool_mode, name)
            group2.add(row)
            self.tool_rows[name] = row

        page3 = Adw.PreferencesPage(title=_("Hlas"), icon_name="audio-input-microphone-symbolic")
        self.add(page3)
        group3 = Adw.PreferencesGroup(title=_("Hlasový režim"))
        page3.add(group3)
        self.voice_on = Adw.SwitchRow(title=_("Povolit hlas"), active=bool(self.cfg.get("voice_enabled")))
        self.voice_on.connect("notify::active", lambda _r, _p: self.save_field("voice_enabled", self.voice_on.get_active()))
        group3.add(self.voice_on)
        self.voice_lang = Adw.ComboRow(
            title=_("Jazyk hlasu"),
            model=Gtk.StringList.new(["Čeština", "English"]),
            selected=0 if self.cfg.get("voice_lang") == "cs" else 1,
        )
        self.voice_lang.connect("notify::selected", lambda _r, _p: self.save_field("voice_lang", "cs" if self.voice_lang.get_selected() == 0 else "en"))
        group3.add(self.voice_lang)

    def save_field(self, key, value):
        self.cfg[key] = value
        config.save(self.cfg)

    def on_provider(self, row, _pspec):
        self.save_field("provider", "ollama" if row.get_selected() == 0 else "openai")

    def on_profile(self, row, _pspec):
        names = ["conservative", "balanced", "full"]
        self.policy = policy_mod.apply_profile(tools.tool_names(), names[row.get_selected()])
        order = [policy_mod.ALLOW, policy_mod.ASK, policy_mod.DENY]
        for name, combo in self.tool_rows.items():
            combo.set_selected(order.index(self.policy[name]))

    def on_tool_mode(self, row, _pspec, name):
        order = [policy_mod.ALLOW, policy_mod.ASK, policy_mod.DENY]
        self.policy[name] = order[row.get_selected()]
        policy_mod.save(self.policy)


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=config.APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = ChatWindow(self)
        win.present()


def main():
    app = App()
    return app.run(sys.argv)
