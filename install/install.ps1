# Installs mneva and connects it to your AI tools. Windows PowerShell 5.1 or later.
#
#   irm https://raw.githubusercontent.com/mneva-ai/mneva/main/install/install.ps1 | iex
#
# In mainland China, set $env:MNEVA_MIRROR='cn' first (README.zh-CN.md has
# the full line): uv, Python and packages then all come from mirrors.
# Safe to run again: what is already installed is left as it is.
#
# Runs inside `iex`, so it never calls `exit` (that would close the user's
# window) and keeps its variables inside the script block.

& {
    $ErrorActionPreference = 'Stop'
    # PowerShell 5.1 draws a progress bar per downloaded chunk, which makes
    # Invoke-WebRequest many times slower.
    $ProgressPreference = 'SilentlyContinue'
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $cn = $env:MNEVA_MIRROR -eq 'cn'
    if ($cn) {
        if (-not $env:UV_DEFAULT_INDEX) {
            # A mirror can be down for hours; take the first that answers.
            # uv records the chosen one, so `mneva upgrade` keeps using it.
            foreach ($candidate in 'https://pypi.tuna.tsinghua.edu.cn/simple',
                                   'https://mirrors.cloud.tencent.com/pypi/simple') {
                try {
                    Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 "$candidate/mneva/" | Out-Null
                    $env:UV_DEFAULT_INDEX = $candidate
                    break
                } catch {
                    Write-Host "$candidate is not reachable, trying the next mirror."
                }
            }
            if (-not $env:UV_DEFAULT_INDEX) { throw 'No PyPI mirror is reachable. Check the network and run this again.' }
        }
        if (-not $env:UV_PYTHON_INSTALL_MIRROR) {
            $env:UV_PYTHON_INSTALL_MIRROR = 'https://registry.npmmirror.com/-/binary/python-build-standalone'
        }
    }
    # CI installs the wheel it just built; users get the published package.
    $package = if ($env:MNEVA_PACKAGE) { $env:MNEVA_PACKAGE } else { 'mneva' }
    $localBin = Join-Path $HOME '.local\bin'

    function Find-Uv {
        $onPath = Get-Command uv -ErrorAction SilentlyContinue
        if ($onPath) { return $onPath.Source }
        # Where the official installer puts uv, in its own order. A fresh
        # install is not on this window's PATH yet.
        $dirs = @($env:UV_INSTALL_DIR, $env:XDG_BIN_HOME, $localBin) | Where-Object { $_ }
        foreach ($dir in $dirs) {
            $exe = Join-Path $dir 'uv.exe'
            if (Test-Path $exe) { return $exe }
        }
        return $null
    }

    function Assert-Success([string]$what) {
        if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)." }
    }

    # GitHub and astral.sh are slow or blocked in mainland China, so uv comes
    # from the wheel astral publishes to PyPI, through the PyPI mirror.
    function Install-UvFromIndex([string]$index) {
        $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'win_arm64' } else { 'win_amd64' }
        $page = "$($index.TrimEnd('/'))/uv/"
        $html = (Invoke-WebRequest -UseBasicParsing $page).Content
        $pattern = 'href="([^"]*?uv-(\d+\.\d+\.\d+)-py3-none-' + $arch + '\.whl)#sha256=([0-9a-f]{64})"'
        $best = [regex]::Matches($html, $pattern) |
            Sort-Object { [version]$_.Groups[2].Value } -Descending |
            Select-Object -First 1
        if (-not $best) { throw "No uv wheel for $arch at $page." }
        $version = $best.Groups[2].Value
        $url = [Uri]::new([Uri]$page, $best.Groups[1].Value).AbsoluteUri
        $wheel = Join-Path ([IO.Path]::GetTempPath()) "uv-$version-$arch.zip"
        Write-Host "Downloading uv $version from $page"
        Invoke-WebRequest -UseBasicParsing $url -OutFile $wheel
        $hash = (Get-FileHash $wheel -Algorithm SHA256).Hash.ToLower()
        if ($hash -ne $best.Groups[3].Value) {
            Remove-Item $wheel
            throw "uv download is corrupt (sha256 $hash does not match the index)."
        }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        New-Item -ItemType Directory -Force $localBin | Out-Null
        $zip = [IO.Compression.ZipFile]::OpenRead($wheel)
        try {
            foreach ($name in 'uv.exe', 'uvx.exe') {
                $entry = $zip.GetEntry("uv-$version.data/scripts/$name")
                if (-not $entry) { throw "The uv wheel has no $name." }
                [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, (Join-Path $localBin $name), $true)
            }
        } finally {
            $zip.Dispose()
            Remove-Item $wheel
        }
    }

    $uv = Find-Uv
    if (-not $uv) {
        Write-Host 'Installing uv, which installs mneva and the Python it needs...'
        if ($cn) {
            Install-UvFromIndex $env:UV_DEFAULT_INDEX
        } else {
            # A child process: the official installer may `exit`, and must
            # not take this script down with it.
            powershell -NoProfile -ExecutionPolicy ByPass -Command 'irm https://astral.sh/uv/install.ps1 | iex'
            Assert-Success 'Installing uv'
        }
        $uv = Find-Uv
        if (-not $uv) { throw 'uv was installed but cannot be found. Open a new terminal and run this again.' }
    }

    Write-Host 'Installing mneva...'
    & $uv tool install $package
    Assert-Success 'Installing mneva'
    $bin = (& $uv tool dir --bin | Out-String).Trim()
    Assert-Success 'Finding the mneva command'

    & (Join-Path $bin 'mneva.exe') setup
    $setupFailed = $LASTEXITCODE -ne 0

    # Later terminals find `mneva` (and uv, which shares the folder by default).
    & $uv tool update-shell
    Assert-Success 'Adding mneva to PATH'

    if ($setupFailed) {
        Write-Warning 'mneva is installed, but setup reported a problem above. Fix it, then run: mneva setup'
    } else {
        Write-Host ''
        Write-Host 'mneva is installed. Open a new terminal to use the mneva command.'
    }
}
