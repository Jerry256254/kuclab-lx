#!/usr/bin/env bash
# Zkompiluje po/*.po do /usr/share/locale (vlastni mini-msgfmt, bez zavislosti).
set -euo pipefail

PO_DIR="${PO_DIR_OVERRIDE:-/usr/share/kuclab/po}"
LOCALEDIR="${LOCALEDIR_OVERRIDE:-/usr/share/locale}"
[ -d "$PO_DIR" ] || { echo "zadne preklady, preskakuji"; exit 0; }

python3 - "$PO_DIR" "$LOCALEDIR" <<'EOF'
import os, struct, sys

def parse_po(path):
    msgs = {}
    msgid = msgstr = None
    section = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith('msgid "'):
                if msgid is not None and msgstr is not None:
                    msgs[msgid] = msgstr
                msgid = line[7:-1]
                msgstr = None
                section = "id"
            elif line.startswith('msgstr "'):
                msgstr = line[8:-1]
                section = "str"
            elif line.startswith('"') and section == "id":
                msgid += line[1:-1]
            elif line.startswith('"') and section == "str":
                msgstr += line[1:-1]
    if msgid is not None and msgstr is not None:
        msgs[msgid] = msgstr
    msgs.pop("", None)
    return msgs

def write_mo(msgs, path):
    msgs = {"": "Content-Type: text/plain; charset=UTF-8\n", **msgs}
    keys = sorted(msgs.keys())
    offsets = []
    ids = strs = b""
    for k in keys:
        ke = k.encode("utf-8")
        ve = msgs[k].encode("utf-8")
        offsets.append((len(ids), len(ke), len(strs), len(ve)))
        ids += ke + b"\x00"
        strs += ve + b"\x00"
    n = len(keys)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + len(ids)
    out = struct.pack("Iiiiiii", 0x950412DE, 0, n, 7 * 4, 7 * 4 + n * 8, 0, 0)
    for o1, l1, o2, l2 in offsets:
        out += struct.pack("ii", l1, o1 + keystart)
    for o1, l1, o2, l2 in offsets:
        out += struct.pack("ii", l2, o2 + valuestart)
    out += ids + strs
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(out)

po_dir = sys.argv[1]
localedir = sys.argv[2]
for fn in sorted(os.listdir(po_dir)):
    if not fn.endswith(".po"):
        continue
    lang = fn[:-3]
    msgs = parse_po(os.path.join(po_dir, fn))
    dest = f"{localedir}/{lang}/LC_MESSAGES/kuclab.mo"
    write_mo(msgs, dest)
    print(f"{fn}: {len(msgs)} retezcu -> {dest}")
EOF

if [ -z "${PO_DIR_OVERRIDE:-}" ]; then
  rm -rf "$PO_DIR"
fi
echo "locales OK"
