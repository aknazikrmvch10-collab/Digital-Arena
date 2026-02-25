$Git = "C:\Program Files\Git\cmd\git.exe"
& $Git branch -M main
& $Git add .
& $Git commit -m "Fix timezone bug for Render MiniApp"
& $Git fetch origin main
& $Git branch --set-upstream-to=origin/main main
& $Git pull origin main --allow-unrelated-histories --no-rebase
& $Git push origin main
