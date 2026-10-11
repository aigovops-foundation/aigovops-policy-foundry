# Start the local demo on Windows 10/11 (Docker Desktop with WSL 2, or Podman Desktop).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$port = if ($env:FOUNDRY_PORT) { $env:FOUNDRY_PORT } else { "8000" }
$engine = if (Get-Command docker -ErrorAction SilentlyContinue) { "docker" } elseif (Get-Command podman -ErrorAction SilentlyContinue) { "podman" } else { $null }
if (-not $engine) { Write-Error "Install Docker Desktop (https://docs.docker.com/desktop/setup/install/windows-install/) or Podman Desktop first."; exit 1 }
Write-Host "Using $engine. Building and starting the Policy Foundry on http://localhost:$port ..."
& $engine compose up --build -d
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  try { if ((Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$port/healthz" -TimeoutSec 2).StatusCode -eq 200) { $ok = $true; break } } catch {}
  Start-Sleep -Seconds 1
}
if (-not $ok) { Write-Error "Timed out. Check: $engine compose logs"; exit 1 }
Write-Host "Ready: http://localhost:$port   (stop with: $engine compose down)"
Start-Process "http://localhost:$port"
