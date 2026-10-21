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

unzip_to() {
    if command -v unzip >/dev/null 2>&1; then
        unzip -q "$1" -d "$2"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m zipfile -e "$1" "$2"
    else
        fail "needs unzip to unpack uv; install unzip, then run this again"
    fi
}

# GitHub and astral.sh are slow or blocked in mainland China, and the USTC uv
# mirror refuses some networks, so uv comes from the wheel astral publishes to
# PyPI, through the PyPI mirror: the same route as install.ps1.
install_uv_from_index() {
    index="${1%/}/uv/"
    case "$(uname -s)-$(uname -m)" in
        Linux-x86_64) tag='manylinux[^"#]*x86_64' ;;
        Linux-aarch64 | Linux-arm64) tag='manylinux[^"#]*aarch64' ;;
        Darwin-arm64) tag='macosx_[0-9_]*arm64' ;;
        Darwin-x86_64) tag='macosx_[0-9_]*x86_64' ;;
        *) fail "no uv wheel for $(uname -s) $(uname -m); install uv yourself, then run this again" ;;
    esac
    # The index is not in version order (0.9.9 sorts after 0.13.4), so put
    # the version in front and sort on its three numbers.
    href=$(download "$index" |
        grep -Eo 'href="[^"]*uv-[0-9.]+-py3-none-'"$tag"'\.whl#sha256=[0-9a-f]{64}"' |
        sed 's|^\(.*/uv-\([0-9.]*\)-py3.*\)$|\2 \1|' |
        sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1 | cut -d' ' -f2)
    [ -n "$href" ] || fail "no uv wheel found at $index"
    url=${href#href=\"}
    url=${url%\"}
    sha=${url##*#sha256=}
    url=${url%%#*}
    # Links on the index are relative; curl and wget resolve the "../".
    case "$url" in http*) ;; *) url="$index$url" ;; esac
    version=$(say "$url" | sed 's|.*/uv-\([0-9.]*\)-py3.*|\1|')

    tmp=$(mktemp -d)
    say "Downloading uv $version from $index"
    download "$url" >"$tmp/uv.whl"
    actual=$( (sha256sum "$tmp/uv.whl" 2>/dev/null || shasum -a 256 "$tmp/uv.whl") | cut -d' ' -f1)
    [ "$actual" = "$sha" ] || fail "uv download is corrupt (sha256 does not match the index)"
    unzip_to "$tmp/uv.whl" "$tmp/wheel"
    mkdir -p "$HOME/.local/bin"
    for name in uv uvx; do
        cp "$tmp/wheel/uv-$version.data/scripts/$name" "$HOME/.local/bin/$name"
        chmod 755 "$HOME/.local/bin/$name"
    done
    rm -rf "$tmp"
}

main() {
    package="${MNEVA_PACKAGE:-mneva}"
    cn=0
    if [ "${MNEVA_MIRROR:-}" = cn ]; then
        cn=1
        : "${UV_DEFAULT_INDEX:=https://pypi.tuna.tsinghua.edu.cn/simple}"
        : "${UV_PYTHON_INSTALL_MIRROR:=https://registry.npmmirror.com/-/binary/python-build-standalone}"
        export UV_DEFAULT_INDEX UV_PYTHON_INSTALL_MIRROR
    fi

    if ! uv=$(find_uv); then
        say "Installing uv, which installs mneva and the Python it needs..."
        if [ "$cn" = 1 ]; then
            install_uv_from_index "$UV_DEFAULT_INDEX"
        else
            download https://astral.sh/uv/install.sh | sh
        fi
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
