param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

$ProjectName = "MousePro"
$PackageBaseName = "MousePro"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ReleaseDir = Join-Path $Root "release"
$BuildDir = Join-Path $Root "build"
$DistDir = Join-Path $Root "dist"
$StageRoot = Join-Path $ReleaseDir "_stage"

function Normalize-Version([string]$Value) {
    $v = $Value.Trim()
    if ($v.StartsWith("v")) {
        $v = $v.Substring(1)
    }
    if ($v -notmatch '^\d+\.\d+\.\d+$') {
        throw "Version must use Semantic Versioning, for example v1.0.0."
    }
    return $v
}

function Next-Patch-Version {
    if (-not (Test-Path -LiteralPath $ReleaseDir)) {
        return "1.0.0"
    }

    $versions = Get-ChildItem -LiteralPath $ReleaseDir -Filter "$PackageBaseName-v*-Windows.zip" -File |
        ForEach-Object {
            if ($_.Name -match "$PackageBaseName-v(\d+)\.(\d+)\.(\d+)-Windows\.zip") {
                [pscustomobject]@{
                    Major = [int]$Matches[1]
                    Minor = [int]$Matches[2]
                    Patch = [int]$Matches[3]
                }
            }
        } |
        Sort-Object Major, Minor, Patch

    if (-not $versions) {
        return "1.0.0"
    }

    $latest = $versions[-1]
    return "$($latest.Major).$($latest.Minor).$($latest.Patch + 1)"
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = Next-Patch-Version
} else {
    $Version = Normalize-Version $Version
}

$VersionTag = "v$Version"
$PackageName = "$PackageBaseName-$VersionTag"
$ZipPath = Join-Path $ReleaseDir "$PackageName-Windows.zip"
$ChecksumPath = "$ZipPath.sha256"
$VersionedReleaseNotes = Join-Path $ReleaseDir "RELEASE_NOTES-$VersionTag.md"
$StageDir = Join-Path $StageRoot $PackageName

if (Test-Path -LiteralPath $ZipPath) {
    throw "Release already exists: $ZipPath"
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

Write-Host "[$ProjectName] Cleaning temporary build artifacts..."
foreach ($path in @($BuildDir, $DistDir, $StageRoot)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

Write-Host "[$ProjectName] Building $VersionTag..."
$env:MOUSEPRO_VERSION = $Version
try {
    & (Join-Path $Root ".venv\Scripts\python.exe") -m PyInstaller (Join-Path $Root "MousePro.spec") --noconfirm
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
} finally {
    Remove-Item Env:\MOUSEPRO_VERSION -ErrorAction SilentlyContinue
}

$BuiltApp = Join-Path $DistDir "MousePro"
if (-not (Test-Path -LiteralPath (Join-Path $BuiltApp "MousePro.exe"))) {
    throw "Build output is missing MousePro.exe: $BuiltApp"
}

Write-Host "[$ProjectName] Staging release..."
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null
Copy-Item -Path (Join-Path $BuiltApp "*") -Destination $StageDir -Recurse -Force

foreach ($doc in @("LICENSE", "README.md", "README_CN.md", "CHANGELOG.md", "RELEASE_NOTES.md")) {
    $src = Join-Path $Root $doc
    if (-not (Test-Path -LiteralPath $src)) {
        throw "Missing release document: $doc"
    }
    Copy-Item -LiteralPath $src -Destination (Join-Path $StageDir $doc) -Force
}

$StageImagesDir = Join-Path $StageDir "images"
New-Item -ItemType Directory -Force -Path $StageImagesDir | Out-Null
foreach ($image in @(
    "Screenshot_mouse_en.png",
    "Screenshot_settings_en.png",
    "Screenshot_generic_en.png",
    "Screenshot_mouse_zh-CN.png",
    "Screenshot_settings_zh-CN.png",
    "Screenshot_generic_zh-CN.png"
)) {
    Copy-Item -LiteralPath (Join-Path $Root "images\$image") -Destination (Join-Path $StageImagesDir $image) -Force
}

Copy-Item -LiteralPath (Join-Path $Root "RELEASE_NOTES.md") -Destination $VersionedReleaseNotes -Force
Copy-Item -LiteralPath (Join-Path $Root "CHANGELOG.md") -Destination (Join-Path $ReleaseDir "CHANGELOG.md") -Force

Write-Host "[$ProjectName] Creating $ZipPath..."
Compress-Archive -LiteralPath $StageDir -DestinationPath $ZipPath -CompressionLevel Optimal

$ZipHash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath $ChecksumPath -Value "$ZipHash  $([System.IO.Path]::GetFileName($ZipPath))" -Encoding ascii

Remove-Item -LiteralPath $StageRoot -Recurse -Force

Write-Host "[$ProjectName] Release complete:"
Write-Host "  $ZipPath"
Write-Host "  $ChecksumPath"
Write-Host "  $VersionedReleaseNotes"
Write-Host "  $(Join-Path $ReleaseDir 'CHANGELOG.md')"
