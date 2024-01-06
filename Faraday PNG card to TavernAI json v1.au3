; Faraday Card to TavernAI json Converter
; made by Elise Windbloom

#include <FileConstants.au3>
#include <WinAPIFiles.au3>
#include <WinAPIGdi.au3>
#include <WinAPIHObj.au3>
#include <MsgBoxConstants.au3>


Global $pngFilePath = FileOpenDialog("Select PNG File", @ScriptDir, "PNG Files (*.png)", 1)
Global $outputJsonFilePath = _GetFileDirectory($pngFilePath) & "\" & _GetFileNameWithoutExtension($pngFilePath) & ".json"


; Check if the user canceled file selection
If $pngFilePath = "" Or $outputJsonFilePath = "" Then
    MsgBox($MB_OK + $MB_ICONERROR, "Error", "File selection canceled.")
    Exit
EndIf

; Open the PNG file in text mode
Global $fileHandle = FileOpen($pngFilePath, $FO_READ + $FO_ANSI)

; Check if the file was opened successfully
If $fileHandle = -1 Then
    MsgBox($MB_OK + $MB_ICONERROR, "Error", "Unable to open the PNG file.")
    Exit
EndIf
; Read the PNG file content
Global $pngFileContent = FileRead($fileHandle) & "2}"
; Close the file handle
FileClose($fileHandle)

;Gets the data
Global $sFullText = StringMidEx($pngFileContent, '{"character":', ',"version":')
Global $sName = StringMidEx($pngFileContent, 'aiName":"', '",')
Global $sPersona = StringMidEx($pngFileContent, 'aiPersona":"', '","basePrompt')
Global $sExample = StringMidEx($pngFileContent, ',"customDialogue":"', '","firstMessage":')
Global $sFirstMsg = StringMidEx($pngFileContent, ',"firstMessage":"', '","grammar"')

;replace \n with enters
;$sPersona = StringReplace($sPersona,"\n",@CRLF & @TAB)
;$sExample = StringReplace($sExample,"\n",@CRLF & @TAB)
;$sFirstMsg = StringReplace($sFirstMsg,"\n",@CRLF & @TAB)

;replace {character} with {char} for tavern
$sPersona = StringReplace($sPersona,"{character}","{char}")
$sExample = StringReplace($sExample,"{character}","{char}")
$sFirstMsg = StringReplace($sFirstMsg,"{character}","{char}")

;format for a json FileChangeDir
Global $outData = '{' & @CRLF & @TAB & _
'"char_name": "' & $sName & '",' & @CRLF & @TAB & _
'"char_persona": "' & $sPersona & '",' & @CRLF & @TAB & _
'"world_scenario": "' & '",' & @CRLF & @TAB & _
'"char_greeting": "' & $sFirstMsg & '",' & @CRLF & @TAB & _
'"example_dialogue": "' & $sExample & '",' & @CRLF & @TAB & _
'"name": "' & $sName & '",' & @CRLF & @TAB & _
'"description": "' & $sPersona & '",' & @CRLF & @TAB & _
'"personality": "' & '",' & @CRLF & @TAB & _
'"scenario": "' & '",' & @CRLF & @TAB & _
'"first_mes": "' & $sFirstMsg & '",' & @CRLF & @TAB & _
'"mes_example": "' & $sExample & '",' & @CRLF & @TAB & _
'"metadata": {' & @CRLF & @TAB & @TAB & _
'"version": 1,' & @CRLF & @TAB & @TAB & _
'"created": 1704465938706,' & @CRLF & @TAB & @TAB & _
'"modified": 1704465938706,' & @CRLF & @TAB & @TAB & _
'"source": null,' & @CRLF & @TAB & @TAB & _
'"tool": {' & @CRLF & @TAB & @TAB & @TAB & _
'"name": "AI Character",' & @CRLF & @TAB & @TAB & @TAB & _
'"version": "0.5.0",' & @CRLF & @TAB & @TAB & @TAB & _
'"url": "None"' & @CRLF & @TAB & @TAB & _
'}' & @CRLF & @TAB & _
'}' & @CRLF & _
'}'


;display to console
ConsoleWrite("$FullText = " & $sFullText & @CRLF & "<==========>" & @CRLF)
ConsoleWrite("$sName = " & $sName & @CRLF & "<==========>" & @CRLF)
ConsoleWrite("$sPersona = " & $sPersona & @CRLF & "<==========>" & @CRLF)
ConsoleWrite("$sExample = " & $sExample & @CRLF & "<==========>" & @CRLF)
ConsoleWrite("$sFirstMsg = " & $sFirstMsg & @CRLF & "<==========>" & @CRLF)

; Save JSON data to a file
Local $hFileOpen = FileOpen($outputJsonFilePath, $FO_OVERWRITE)
If $hFileOpen = -1 Then
   MsgBox($MB_SYSTEMMODAL, "", "An error occurred whilst writing the temporary file.")
   Exit
EndIf

If FileWrite($hFileOpen, $outData) == 0 Then
   MsgBox($MB_ICONINFORMATION, "Error", "Error while writing JSON data extracted to " & $outputJsonFilePath)
Else
   MsgBox($MB_ICONINFORMATION, "Success", "JSON data extracted and saved to " & $outputJsonFilePath)
EndIf




;============Functions
;------------------------------------------------

Func StringMidEx($sInput, $sStartDelimiter, $sEndDelimiter, $iStartOccurrence=1, $iEndOccurrence=1)
   ;returns the sting between two substrings(delimiters)
   ;don't give negative numbers, will use who start/end automatically if it doesn't find occurrences
   Local $iStartPos = 1
   Local $iEndPos = 0

   ; Find the start delimiter based on occurrence

   $iStartPos = StringInStr($sInput, $sStartDelimiter, 1, $iStartOccurrence, 1)
   $iEndPos = StringInStr($sInput, $sEndDelimiter, 1, $iEndOccurrence, $iStartPos)

   ;ConsoleWrite("$iStartPos="&$iStartPos&" $iEndPos="&$iEndPos&" Count="&($iEndPos - $iStartPos)&@CRLF)

   ; Extract the substring between start and end delimiters
   Return StringMid($sInput, $iStartPos+StringLen($sStartDelimiter), $iEndPos - $iStartPos - StringLen($sStartDelimiter))
EndFunc

Func _GetFileDirectory($filePath)
    ; Check if the file path contains a directory separator
    Local $separatorPos = StringInStr($filePath, "\", 0, -1)

    If $separatorPos Then
        ; Extract the directory part using StringLeft
        Return StringLeft($filePath, $separatorPos - 1)
    Else
        ; If no separator is found, return an empty string or the original path
        Return ""
    EndIf
EndFunc

Func _GetFileNameWithoutExtension($filePath)
    ; Extract the file name without extension using StringSplit
    Local $split = StringSplit($filePath, "\")
    Local $fileName = $split[$split[0]]

    ; Check if the file name contains a dot (.)
    Local $dotPos = StringInStr($fileName, ".", 0, -1)

    If $dotPos Then
        ; If a dot is found, extract the substring before the dot
        Return StringLeft($fileName, $dotPos - 1)
    Else
        ; If no dot is found, return the original file name
        Return $fileName
    EndIf
EndFunc
