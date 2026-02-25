$Git = "C:\Program Files\Git\cmd\git.exe"
& $Git config --global user.name "AI Assistant"
& $Git config --global user.email "bot@example.com"
& $Git init
& $Git remote add origin https://github.com/aknazikrmvch10-collab/Digital-Arena.git
& $Git fetch origin
& $Git checkout -B main origin/main
& $Git add .
& $Git commit -m "Fix timezone bug for Render MiniApp"
Write-Host "Triggering Git Push. Please check your screen for a Github Login Popup!"
& $Git push origin main
