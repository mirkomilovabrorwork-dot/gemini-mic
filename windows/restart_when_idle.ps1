# Restart Gemini Mic only when the owner is not dictating (11-08: a blind restart cut 2 takes).
# Waits until state.txt says idle and has not changed for 20 s (max 10 min), then restarts.
$state = Join-Path $env:APPDATA "GeminiMic\state.txt"
$deadline = (Get-Date).AddMinutes(10)
while ((Get-Date) -lt $deadline) {
    if (Test-Path $state) {
        $s = (Get-Content $state -Raw).Trim()
        $age = ((Get-Date) - (Get-Item $state).LastWriteTime).TotalSeconds
        if ($s -eq "idle" -and $age -ge 20) { break }
    } else { break }
    Start-Sleep -Seconds 2
}
if ((Get-Date) -ge $deadline) { Write-Output "not idle for 10 min - not restarted"; exit 1 }
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'pythonw.*gemini_mic' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Seconds 1
Start-Process -FilePath (Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe") -ArgumentList "gemini_mic.py" -WorkingDirectory $PSScriptRoot
Write-Output "restarted $(Get-Date -Format HH:mm:ss)"
