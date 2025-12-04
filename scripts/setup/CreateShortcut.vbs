Set oWS = WScript.CreateObject("WScript.Shell")
sStartup = oWS.SpecialFolders("Startup")
sLinkFile = sStartup & "\InsiderTradingScheduler.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "C:\Users\MM\anaconda3\pythonw.exe"
oLink.Arguments = """c:\Users\MM\expedientes-app\trading\Bot2\auto_scheduler.py"""
oLink.WorkingDirectory = "c:\Users\MM\expedientes-app\trading\Bot2"
oLink.Description = "Insider Trading Auto Scheduler"
oLink.WindowStyle = 7
oLink.Save

WScript.Echo "Acceso directo creado en: " & sLinkFile
