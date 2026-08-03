param(
    [string]$Repository = "CantorAI/ModelZoo",
    [string]$Dist = "dist",
    [switch]$Draft
)
$ErrorActionPreference = "Stop"
Get-ChildItem -LiteralPath $Dist -Directory | ForEach-Object {
    $manifest = Get-Content -Raw -LiteralPath (Join-Path $_.FullName "release-manifest.json") | ConvertFrom-Json
    $tag = $manifest.tag
    $title = "$($manifest.model_id) v$($manifest.version)"
    $arguments = @("release", "create", $tag, "--repo", $Repository, "--title", $title,
        "--notes", "Signed Garnet ModelZoo artifact set. See release-manifest.json for file digests.")
    if ($Draft) { $arguments += "--draft" }
    if (-not (gh release view $tag --repo $Repository 2>$null)) {
        & gh @arguments
    }
    Get-ChildItem -LiteralPath $_.FullName -File | ForEach-Object {
        & gh release upload $tag $_.FullName --repo $Repository --clobber
    }
}
