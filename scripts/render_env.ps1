param(
    [string]$ApiKey = $env:RENDER_API_KEY,
    [string]$ServiceName = "subtrack-api"
)

<#
Настройка env-переменных на Render (service subtrack-api) через Render API.

Требуется API-ключ Render: dashboard.render.com -> Account Settings -> API Keys
Задать можно так:  $env:RENDER_API_KEY = "rnd_xxx"; .\scripts\render_env.ps1

Источник значений (приоритет):
  1) файл scripts/render_env.json (НЕ коммитится)  {"ИМЯ": "значение"}
  2) уже установленные на Render переменные
  3) интерактивный промпт
  4) YOOMONEY_NOTIFY_SECRET генерируется автоматически, если не задан
#>

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Write-Host "RENDER_API_KEY не задан." -ForegroundColor Red
    Write-Host "1) Создайте ключ: dashboard.render.com -> Account Settings -> API Keys -> Create API Key"
    Write-Host "2) Выполните:  `$env:RENDER_API_KEY = 'rnd_...'; .\scripts\render_env.ps1"
    exit 1
}

$base = "https://api.render.com/v1"
$headers = @{ Authorization = "Bearer $ApiKey" }

function Invoke-Render($Method, $Path, $BodyJson = $null) {
    $args = @{ Uri = "$base$Path"; Method = $Method; Headers = $headers; TimeoutSec = 60 }
    if ($BodyJson) {
        $args.ContentType = "application/json"
        $args.Body = $BodyJson
    }
    return Invoke-RestMethod @args
}

Write-Host "Ищу сервис '$ServiceName'..." -ForegroundColor Cyan
$services = Invoke-Render GET "/services?name=$([uri]::EscapeDataString($ServiceName))&limit=20"
$svc = $services | Where-Object { $_.service.name -eq $ServiceName } | Select-Object -First 1
if (-not $svc) {
    Write-Host "Сервис '$ServiceName' не найден. Найденные:" -ForegroundColor Red
    $services | ForEach-Object { Write-Host "  $($_.service.name)" }
    exit 1
}
$svcId = $svc.service.id
Write-Host "Сервис: $($svc.service.name) (id=$svcId)" -ForegroundColor Green

$current = @{}
try {
    $envs = Invoke-Render GET "/services/$svcId/env-vars?limit=100"
    foreach ($e in $envs) {
        if ($e.envVar.value) { $current[$e.envVar.key] = $e.envVar.value }
    }
    Write-Host "`nТекущие переменные на сервисе:" -ForegroundColor Cyan
    if ($current.Keys.Count -eq 0) { Write-Host "  (пусто)" }
    $current.Keys | Sort-Object | ForEach-Object {
        $v = $current[$_]
        $masked = if ($_.ToString().ToUpper() -match "TOKEN|SECRET|PASSWORD|DATABASE_URL") { "$($v.Substring(0, [Math]::Min(6, $v.Length)))..." } else { $v }
        Write-Host "  $_ = $masked"
    }
}
catch { Write-Host "Не удалось прочитать переменные: $($_.Exception.Message)" -ForegroundColor Yellow }

$json = @{}
$jsonPath = Join-Path $PSScriptRoot "render_env.json"
if (Test-Path $jsonPath) {
    try { $json = Get-Content $jsonPath -Raw | ConvertFrom-Json }
    catch { Write-Host "Не прочитан render_env.json: $($_.Exception.Message)" -ForegroundColor Yellow }
}

$want = @("YOOMONEY_WALLET", "YOOMONEY_TOKEN", "YOOMONEY_NOTIFY_SECRET", "TG_BOT_TOKEN", "DATABASE_URL", "OWNER_TG_CHAT_ID", "OWNER_EMAIL")
$toSet = @{}

foreach ($k in $want) {
    $fromJson = [string]$json.$k
    $already = [string]$current[$k]
    if (-not [string]::IsNullOrWhiteSpace($fromJson)) {
        $toSet[$k] = $fromJson.Trim()
        Write-Host "`n$k : беру из render_env.json" -ForegroundColor Green
    }
    elseif (-not [string]::IsNullOrWhiteSpace($already)) {
        Write-Host "`n$k : уже задан, пропускаю" -ForegroundColor DarkGray
    }
    elseif ($k -eq "YOOMONEY_NOTIFY_SECRET") {
        $toSet[$k] = -join ((48..57) + (97..102) + (65..90) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
        Write-Host "`nYOOMONEY_NOTIFY_SECRET : сгенерирован автоматически" -ForegroundColor Yellow
    }
    else {
        $val = Read-Host "`n$k (Enter - пропустить)"
        if ($val) { $toSet[$k] = $val }
    }
}

Write-Host "`nУстанавливаю на Render..." -ForegroundColor Cyan
$changed = @()
foreach ($k in $toSet.Keys | Sort-Object) {
    $v = $toSet[$k]
    $body = @{ value = $v } | ConvertTo-Json -Compress
    try {
        Invoke-Render PUT "/services/$svcId/env-vars/$k" $body | Out-Null
        $changed += $k
        Write-Host "  OK  $k" -ForegroundColor Green
    }
    catch {
        Write-Host "  FAIL $k : $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nУстановлено: $($changed -join ', ')" -ForegroundColor Green
if ($changed -contains "YOOMONEY_NOTIFY_SECRET") {
    Write-Host "`n!! ВАЖНО: YOOMONEY_NOTIFY_SECRET = $($toSet['YOOMONEY_NOTIFY_SECRET'])" -ForegroundColor Yellow
    Write-Host "Этот же пароль впишите в ЮMoney: Кошелёк -> Настройки -> Уведомления -> HTTP-уведомления -> пароль уведомлений."
}
Write-Host "`nRender перезапустит сервис автоматически. Осталась ручная настройка только в ЮMoney (см. scripts/yoomoney_checklist.md)."
