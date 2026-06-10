' Hidden launcher for run_sync.bat
' Runs the hourly Xero -> SQL sync with NO visible Command Prompt window.
' (Window style 0 = hidden; False = don't wait.)
Dim sBat
sBat = "C:\Users\AnthonyPenzes\Desktop\FSA Debtor System\Debitor-main\run_sync.bat"
CreateObject("WScript.Shell").Run """" & sBat & """", 0, False
