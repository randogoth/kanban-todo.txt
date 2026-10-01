#!/usr/bin/env bash
# Installs kbtd.py and its index.html into one directory and symlinks
# the script onto your PATH, so `kbtd` runs from any folder.
set -euo pipefail

SOURCE_URL="${KBTD_SOURCE_URL:-https://raw.githubusercontent.com/randogoth/kanban-todo.txt/main}"
INSTALL_DIR="${KBTD_INSTALL_DIR:-$HOME/.local/share/kbtd}"
BIN_DIR="${KBTD_BIN_DIR:-$HOME/.local/bin}"

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

echo "Installing kbtd to $INSTALL_DIR ..."
curl -fsSL -o "$INSTALL_DIR/kbtd.py" "$SOURCE_URL/kbtd.py"
curl -fsSL -o "$INSTALL_DIR/index.html" "$SOURCE_URL/index.html"
chmod 755 "$INSTALL_DIR/kbtd.py"

ln -sf "$INSTALL_DIR/kbtd.py" "$BIN_DIR/kbtd"

echo "Installed. Run 'kbtd <path-to-todo.txt>' from any folder."

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo ""
        echo "Note: $BIN_DIR is not on your PATH. Add it, e.g.:"
        echo "  export PATH=\"$BIN_DIR:\$PATH\""
        ;;
esac
