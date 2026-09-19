import Gio from 'gi://Gio';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

const CHAT_APP = 'org.kuclab.AgentChat.desktop';

export default class KucLabAgentExtension extends Extension {
    enable() {
        this._button = new St.Bin({
            style_class: 'panel-button kuclab-agent-button',
            reactive: true,
            can_focus: true,
            track_hover: true,
            child: new St.Icon({
                gicon: Gio.ThemedIcon.new('org.kuclab.AgentChat'),
                style_class: 'system-status-icon',
            }),
        });
        this._button.connect('button-press-event', () => this._openChat());
        Main.panel.addToStatusArea('kuclab-agent', this._button, 1, 'right');

        Main.wm.addKeybinding(
            'kuclab-agent-chat',
            new Gio.Settings({ schema_id: 'org.gnome.shell.extensions.kuclab-agent' }),
            0,
            0,
            () => this._openChat(),
        );
    }

    disable() {
        Main.wm.removeKeybinding('kuclab-agent-chat');
        this._button?.destroy();
        this._button = null;
    }

    _openChat() {
        Gio.DesktopAppInfo.new(CHAT_APP)?.launch([], null);
    }
}
