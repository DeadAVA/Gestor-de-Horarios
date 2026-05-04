Set oShell = CreateObject("WScript.Shell")
Dim exePath
exePath = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\")) & "HorariosUABCPortable.exe"
oShell.Run Chr(34) & exePath & Chr(34), 0, False
Set oShell = Nothing
