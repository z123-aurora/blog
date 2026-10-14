# Run pytest -v in a real cmd window and capture a native screenshot of that window
$ErrorActionPreference = 'Stop'
$proj   = 'd:\Trae CN\lianxi\blog'
$outPng = Join-Path $proj 'reports\pytest_result.png'

# Inner command: UTF-8 codepage -> fixed window title -> resize -> run pytest -> keep alive
$cmdLine = '/c "chcp 65001 >nul && title PYTEST_RESULT && mode con: cols=124 lines=50 && cd /d ""d:\Trae CN\lianxi\blog"" && set PYTHONDONTWRITEBYTECODE=1 && python -m pytest -v -p no:cacheprovider --color=no && echo. && echo ================ ALL TESTS PASSED ================ && pause >nul"'

$p = Start-Process cmd.exe -ArgumentList $cmdLine -PassThru

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class WinApi {
    [DllImport("user32.dll")] public static extern IntPtr FindWindow(string c, string n);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@

# Wait for the window to appear (up to 15s)
$hwnd = [IntPtr]::Zero
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    $hwnd = [WinApi]::FindWindow($null, 'PYTEST_RESULT')
    if ($hwnd -ne [IntPtr]::Zero) { break }
}
if ($hwnd -eq [IntPtr]::Zero) { throw 'pytest window not found' }

# pytest takes ~4-6s; wait extra so all 70 result lines and the summary are printed
Start-Sleep -Seconds 10
[WinApi]::ShowWindow($hwnd, 9) | Out-Null          # SW_RESTORE
[WinApi]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Seconds 1

$rect = New-Object WinApi+RECT
[WinApi]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
$w = $rect.Right - $rect.Left
$h = $rect.Bottom - $rect.Top

$bmp = New-Object System.Drawing.Bitmap($w, $h)
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$bmp.Save($outPng, [System.Drawing.Imaging.ImageFormat]::Png)
$gfx.Dispose()
$bmp.Dispose()

Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
if (Test-Path $outPng) {
    $f = Get-Item $outPng
    Write-Output ("SAVED: {0} ({1} bytes)" -f $f.FullName, $f.Length)
} else {
    throw 'screenshot file was not created'
}
