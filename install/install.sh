#!/bin/sh
# Installs mneva and connects it to your AI tools. macOS and Linux.
#
#   curl -LsSf https://raw.githubusercontent.com/mneva-ai/mneva/main/install/install.sh | sh
#
# In mainland China, run it with MNEVA_MIRROR=cn (README.zh-CN.md has the full
# line): uv, Python and packages then all come from mirrors.
# Safe to run again: what is already installed is left as it is.
#
# Everything is inside main(), called on the last line, so a `curl | sh` run
# has read the whole script before any command can read from stdin.
set -eu

USTC_UV=https://mirrors.ustc.edu.cn/github-release/astral-sh/uv/LatestRelease

say() { printf '%s\n' "$*"; }
fail() { say "mneva install: $*" >&2; exit 1; }

download() {
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf "$1"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "$1"
    else
        fail "needs curl or wget to download $1"
    fi
}

# Where the official installer puts uv, in its own order. A fresh install is
# not on this shell's PATH yet.
find_uv() {
    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return 0
    fi
    for dir in "${UV_INSTALL_DIR:-}" "${XDG_BIN_HOME:-}" \
        "${XDG_DATA_HOME:+$XDG_DATA_HOME/../bin}" "$HOME/.local/bin"; do
        if [ -n "$dir" ] && [ -x "$dir/uv" ]; then
            say "$dir/uv"
            return 0
        fi
    done
    return 1
}

main() {
    package="${MNEVA_PACKAGE:-mneva}"
    uv_installer=https://astral.sh/uv/install.sh
    if [ "${MNEVA_MIRROR:-}" = cn ]; then
        : "${UV_DEFAULT_INDEX:=https://pypi.tuna.tsinghua.edu.cn/simple}"
        : "${UV_PYTHON_INSTALL_MIRROR:=https://registry.npmmirror.com/-/binary/python-build-standalone}"
        # The installer carries checksums for its own uv version, so it and
        # the binaries must come from the same mirror folder.
        uv_installer="$USTC_UV/uv-installer.sh"
        : "${UV_DOWNLOAD_URL:=$USTC_UV}"
        export UV_DEFAULT_INDEX UV_PYTHON_INSTALL_MIRROR UV_DOWNLOAD_URL
    fi

    if ! uv=$(find_uv); then
        say "Installing uv, which installs mneva and the Python it needs..."
        download "$uv_installer" | sh
        uv=$(find_uv) || fail "uv was installed but cannot be found. Open a new terminal and run this again."
    fi

    say "Installing mneva..."
    "$uv" tool install "$package" </dev/null
    bin=$("$uv" tool dir --bin)

    setup_ok=1
    "$bin/mneva" setup </dev/null || setup_ok=0

    # Later terminals find `mneva` (and uv, which shares the folder by default).
    "$uv" tool update-shell </dev/null

    if [ "$setup_ok" = 1 ]; then
        say ""
        say "mneva is installed. Open a new terminal to use the mneva command."
    else
        say "mneva is installed, but setup reported a problem above. Fix it, then run: mneva setup" >&2
    fi
}

main "$@"
