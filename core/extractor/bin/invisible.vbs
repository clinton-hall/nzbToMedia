set args = WScript.Arguments
num = args.Count

if num < 2 then
    WScript.Echo "Usage: [CScript | WScript] invis.vbs aScript.bat <visible or invisible 1/0> <some script arguments>"
    WScript.Quit 1
end if

sargs = ""
if num > 2 then
    sargs = " "
    for k = 2 to num - 1
        anArg = args.Item(k)
        sargs = sargs & anArg & " "
    next
end if

Set WshShell = WScript.CreateObject("WScript.Shell")

returnValue = WshShell.Run("""" & args(1) & """" & sargs, args(0), True)
WScript.Quit(returnValue)
