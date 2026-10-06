' Gemini Mic watchdog - run every minute by the "GeminiMicWatchdog" scheduled
' task. If no pythonw.exe is running gemini_mic.py, start it hidden.
' A double start is harmless: the app's own named mutex makes the second copy
' exit. Owner chose this 2026-10-06 after the app was found closed 3 times.
Option Explicit
Dim wmi, procs, p, alive, dir, sh
dir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery("SELECT CommandLine FROM Win32_Process WHERE Name='pythonw.exe'")
alive = False
For Each p In procs
  If Not IsNull(p.CommandLine) Then
    If InStr(1, p.CommandLine, "gemini_mic.py", vbTextCompare) > 0 Then alive = True
  End If
Next
If Not alive Then
  Set sh = CreateObject("WScript.Shell")
  sh.CurrentDirectory = dir
  sh.Run """" & dir & "\.venv\Scripts\pythonw.exe"" gemini_mic.py", 0, False
End If
