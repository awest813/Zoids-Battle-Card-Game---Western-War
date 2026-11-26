# Launch an isolated Zoids REFERENCE runtime with the current localization.
param(
    [switch]$Headless,
    [switch]$HeadlessOpenGL,
    [switch]$Capture,
    [switch]$TextureDump,
    [switch]$NoTextures,
    [string]$ProjectDir = (Join-Path $env:USERPROFILE "zoids-recomp\zoids-battle-card-game"),
    [string]$ToolchainBin = (Join-Path $env:USERPROFILE ".local\share\retcomm\toolchains\cmake-clang-v1\latest\bin"),
    [string]$BuildDir = "build-reference",
    [ValidateRange(1, 65535)][int]$Port = 4371,
    [ValidateSet("jp", "en")][string]$Lang = "jp",
    [string]$Log = "",
    [string]$SaveDir = ""
)
$ErrorActionPreference = "Stop"
if ($Headless -and $HeadlessOpenGL) { throw "Choose one headless renderer." }

$workspace = Split-Path -Parent $PSScriptRoot
$project = (Resolve-Path -LiteralPath $ProjectDir).Path
$build = Join-Path $project $BuildDir
$exeName = "ZoidsBattleCardGame.exe"
if (!(Test-Path -LiteralPath (Join-Path $build $exeName) -PathType Leaf)) {
    throw "Build not found in $build"
}
$english = $Lang -eq "en"
$runtimeExe = Join-Path $build $exeName
if ($english) {
    $runtimeExe = python -B -X utf8 (Join-Path $PSScriptRoot "build_safe_runtime.py") --project-dir $project --toolchain-bin $ToolchainBin --build-dir $BuildDir
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $runtimeExe -PathType Leaf)) {
        throw "Could not build the isolated English runtime."
    }
}
$cue = Join-Path $workspace "Zoids - Battle Card Game - Seihou Tairiku Senki (Japan).cue"
$retailExe = Join-Path $workspace "extracted\SLPS_032.55"
if (!(Test-Path -LiteralPath $cue -PathType Leaf) -or !(Test-Path -LiteralPath $retailExe -PathType Leaf)) {
    throw "Place the retail CUE/BIN in the project root and run python tools/extract.py first."
}
$stage = Join-Path $workspace "work\localization-runtime\$Port"
$config = Join-Path $stage "game.toml"
$activeTables = Join-Path $stage "translations"
$tableNames = @("zoids.phase2_hash.toml", "zoids.pointer_pending.toml", "zoids.card_short.toml")

New-Item -ItemType Directory -Force -Path $activeTables, (Join-Path $stage "disc") | Out-Null
$unexpected = Get-ChildItem -LiteralPath $activeTables -Filter "*.toml" -File |
    Where-Object { $_.Name -notin $tableNames }
if ($unexpected) { throw "Unexpected runtime translation tables in ${activeTables}: $($unexpected.Name -join ', ')" }
foreach ($name in $tableNames) {
    $source = Join-Path $workspace "translations\$name"
    if (Select-String -LiteralPath $source -Pattern '^\s*ram_addr\s*=' -Quiet) {
        throw "Unsafe in-place translation entry in $source"
    }
    Copy-Item -LiteralPath $source -Destination $activeTables -Force
}
Copy-Item -LiteralPath $runtimeExe -Destination (Join-Path $stage $exeName) -Force
foreach ($name in @("ZoidsBattleCardGame.execution.json", "game.toml", "game_options.toml", "bios", "assets")) {
    $source = Join-Path $build $name
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination $stage -Recurse -Force
    }
}
Copy-Item -LiteralPath $retailExe -Destination (Join-Path $stage "disc") -Force
if (!(Test-Path -LiteralPath $config -PathType Leaf)) { throw "Missing game.toml in $build" }
if (!$SaveDir) { $SaveDir = Join-Path $stage "saves" }
$SaveDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($SaveDir)

$pack = Join-Path $workspace "work\localization-textures\SLPS-03255"
$replace = !$NoTextures -and ($Lang -eq "en") -and (Test-Path -LiteralPath (Join-Path $pack "replacements") -PathType Container) -and
    [bool](Get-ChildItem -LiteralPath (Join-Path $pack "replacements") -Filter "*.png" -File | Select-Object -First 1)
$enable = $replace -or $TextureDump
$mods = Join-Path $stage "mods"
New-Item -ItemType Directory -Force -Path $mods | Out-Null
$bundled = Join-Path $build "mods\bundled"
if (Test-Path -LiteralPath $bundled -PathType Container) {
    Copy-Item -LiteralPath $bundled -Destination $mods -Recurse -Force
}
$latinFirst = $english
$installed = Join-Path $mods "installed"
New-Item -ItemType Directory -Force -Path $installed | Out-Null
Copy-Item -LiteralPath (Join-Path $workspace "mods\zoids.localization.latin-keypad") -Destination $installed -Recurse -Force
$packPath = $pack.Replace('\', '/').Replace('"', '\"')
$modState = @"
format_version = 2

[[package]]
id = "psx.enhancement.hd-textures"

[[feature]]
package_id = "psx.enhancement.hd-textures"
id = "hd-textures"
enabled = $("$enable".ToLowerInvariant())
[feature.values]
dump = "$("$TextureDump".ToLowerInvariant())"
replacements = "$("$replace".ToLowerInvariant())"
[feature.resources]
pack = "$packPath"

[[package]]
id = "psx.enhancement.8mb-ram"
version = "1.0.0"

[[feature]]
package_id = "psx.enhancement.8mb-ram"
id = "8mb-ram"
enabled = $("$english".ToLowerInvariant())

[[package]]
id = "zoids.localization.latin-keypad"
version = "1.0.0"

[[feature]]
package_id = "zoids.localization.latin-keypad"
id = "latin-first"
enabled = $("$latinFirst".ToLowerInvariant())
"@
[IO.File]::WriteAllText((Join-Path $mods "state.toml"), $modState)

$env:PSX_XLATE_CAPTURE = if ($Capture) { "1" } else { "0" }
$env:PSX_LANG = $Lang
$env:PSX_STARVATION_TIMEOUT_US = "0"
$argLine = "--no-launcher --game `"$config`" --disc `"$cue`" --memcard-dir `"$SaveDir`" --debug-port $Port"
if ($Headless) { $argLine = "--headless $argLine" }
if ($HeadlessOpenGL) { $argLine = "--headless-opengl $argLine" }
$launch = @{
    FilePath = Join-Path $stage $exeName
    ArgumentList = $argLine
    WorkingDirectory = $stage
    PassThru = $true
}
if ($Headless -or $HeadlessOpenGL) { $launch.WindowStyle = "Hidden" }
if ($Log) {
    $launch.RedirectStandardOutput = "$Log.out"
    $launch.RedirectStandardError = "$Log.err"
}
$process = Start-Process @launch
Write-Output "Launched PID $($process.Id) on port $Port ($Lang). Config: $config"
