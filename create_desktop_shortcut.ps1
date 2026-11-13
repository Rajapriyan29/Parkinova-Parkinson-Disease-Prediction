$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)

# Primary Parkinova target, with fallback to existing NeuroScanAI build if Parkinova.exe not built yet
$TargetExe = "$PSScriptRoot\dist\Parkinova\Parkinova.exe"
$WorkingDir = "$PSScriptRoot\dist\Parkinova"
if (-not (Test-Path $TargetExe) -and (Test-Path "$PSScriptRoot\dist\NeuroScanAI\NeuroScanAI.exe")) {
    $TargetExe = "$PSScriptRoot\dist\NeuroScanAI\NeuroScanAI.exe"
    $WorkingDir = "$PSScriptRoot\dist\NeuroScanAI"
}

$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Parkinova.lnk")
$Shortcut.TargetPath = $TargetExe
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.IconLocation = "$PSScriptRoot\assets\logo.ico"
$Shortcut.Description = "Parkinova - Parkinson MRI Analysis System"
$Shortcut.Save()
Write-Host "Desktop shortcut created successfully at: $DesktopPath\Parkinova.lnk"
