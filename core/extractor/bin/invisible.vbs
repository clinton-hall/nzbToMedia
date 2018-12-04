set args = WScript.Arguments
num = args.Count

if num = 0 then
    WScript.Echo "Usage: [CScript | WScript] invis.vbs aScript.bat <some script arguments>"
    WScript.Quit 1
end if

sargs = ""
if num > 1 then
    sargs = " "
    for k = 1 to num - 1
        anArg = args.Item(k)
        sargs = sargs & anArg & " "
    next
end if

Set WshShell = WScript.CreateObject("WScript.Shell")

WshShell.Run """" & WScript.Arguments(0) & """" & sargs, 0, True