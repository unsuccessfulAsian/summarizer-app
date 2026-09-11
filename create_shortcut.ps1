$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\YouTube Summarizer.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\run.bat"
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.IconLocation = "shell32.dll,220"
$Shortcut.Save()
Write-Host "Shortcut created on your Desktop."
