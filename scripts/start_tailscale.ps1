# start_tailscale.ps1 - starts SubPing proxy and HTTPS serve via Tailscale.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $here
$port = 8000
$ts = "C:\Program Files\Tailscale\tailscale.exe"

function Log($msg) {
    Write-Output ("{0:HH:mm:ss} {1}" -f (Get-Date), $msg)
}

# 1) Proxy on :8000 (frontend static + /api reverse proxy to render.com via Clash)
$listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    Log "1) Starting proxy.py..."
    Start-Process python -ArgumentList "$here\proxy.py" `
        -RedirectStandardOutput "$here\proxy.out.log" `
        -RedirectStandardError "$here\proxy.err.log" -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Log "1) proxy.py already running"
}

# 2) HTTPS serving via Tailscale (tailscaled renews the certificate automatically)
& $ts serve reset 2>&1 | Out-Null
& $ts serve --bg $port 2>&1 | Out-Null

$json = & $ts status --json | Out-String
$st = $json | ConvertFrom-Json
$dns = $st.Self.DNSName
$url = "https://" + $dns.TrimEnd('.')
$url | Set-Content "$here\tunnel_url.txt" -Encoding Ascii
Log "2) Ready: $url"
Log "   Site and API are available on the Tailscale network at this address."
