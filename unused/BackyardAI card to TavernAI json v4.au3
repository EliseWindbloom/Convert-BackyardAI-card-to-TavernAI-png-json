;Program: BackyardAI(previously known as Faraday) Card to TavernAI json
;Made By: Elise Windbloom
;Notes: v1 - initial release
;	    v2 - bug fixs and more stable
;       v3 - added support for older(?) faraday cards to be converted as well (using unicode mode)
;            (note there seems to artifacts where characters like ' should be for these older cards)
;            (Looks like you can get around this for now by duplicating the character in Faraday then exporting that dulicated character as a PNG)
;		v4 - updated code to support faraday's current base64 format of the character data in the png

#include <FileConstants.au3>
#include <WinAPIFiles.au3>
#include <WinAPIGdi.au3>
#include <WinAPIHObj.au3>
#include <MsgBoxConstants.au3>
#include <Array.au3>

Global $pngFilePath = FileOpenDialog("Select PNG File", @ScriptDir, "PNG Files (*.png)", 1)
Global $outputJsonFilePath = _GetFileDirectory($pngFilePath) & "\" & _GetFileNameWithoutExtension($pngFilePath) & ".json"

; Check if the user canceled file selection
If $pngFilePath = "" Or $outputJsonFilePath = "" Then
    MsgBox($MB_OK + $MB_ICONERROR, "Error", "File selection canceled.")
    Exit
EndIf

; Copy the original file to a new file, overwrite
; this copy is needed because you can't reopen a file in a different encoding mode later
Global $pngFilePathCopy = _GetFileDirectory($pngFilePath)&"\"&_GetFileNameWithoutExtension($pngFilePath)&"_temp.png"
If FileCopy($pngFilePath, $pngFilePathCopy, 1) == 0 Then
   MsgBox($MB_OK + $MB_ICONERROR, "Error", "Unable to make a temp copy of the PNG file.")
   Exit
EndIf


;==Open the PNG file in text ansi mode
Global $fileHandle = FileOpen($pngFilePath, $FO_READ + $FO_ANSI)
; Check if the file was opened successfully
If $fileHandle = -1 Then
    MsgBox($MB_OK + $MB_ICONERROR, "Error", "Unable to open the PNG file.")
    Exit
EndIf
; Read the PNG file content then close
Global $pngFileContent = FileRead($fileHandle) & "2}"
FileClose($fileHandle)

;==Open the PNG file in text unicode mode
Global $fileHandle2 = FileOpen($pngFilePath, $FO_READ + $FO_UNICODE)
; Check if the file was opened successfully
If $fileHandle2 = -1 Then
    MsgBox($MB_OK + $MB_ICONERROR, "Error", "Unable to open the PNG file.")
    Exit
EndIf
; Read the PNG file content then close
Global $pngFileContentUnicode = FileRead($fileHandle2) & "2}"
FileClose($fileHandle2)
FileDelete($pngFilePathCopy);delete the copy

;Gets the data
Global $sDataType = ""
Global $sFullText = StringMidEx($pngFileContent, 'ASCII', 'Q==') & "Q=="
If StringLen($sFullText)>3 Then ;has base64 data
   $sDataType = "base64"
   $sFullText = _GetPNGExtraBase64Data($pngFilePath) ;decodes base64 data
   $pngFileContent = $sFullText
Else;card might be an older (deperciated?) format with plain text/unicode
   $sFullText = StringMidEx($pngFileContent, '{"character":', ',"version":')
   If StringInStr($pngFileContent,'{"character":') == 0 then;data might be unicode format
	  $sDataType = "unicode"
	  $pngFileContent=$pngFileContentUnicode
	  $sFullText = StringMidEx($pngFileContent, '{"character":', ',"version":')

	  ;$sFullText = StringReplace($sFullText,"⁮⁽","'");fixes ' character for unicode data
	  ; Replace the superscript left parenthesis with a regular left parenthesis
	  $sFullText = StringReplace($sFullText, ChrW(0x207D), '')
	  ; Replace the problematic character with a replacement of your choice (e.g., an empty string)
	  $sFullText = StringReplace($sFullText, ChrW(0x0019), "'")
   Else;data might be plain text in ANSI format
	  $sDataType = "ANSI"
   EndIf
EndIf

If $sDataType=="" Then
   MsgBox(0, "Error", "unable to find data type")
   Exit
EndIf

Global $sName = StringMidEx($pngFileContent, 'aiName":"', '",')
Global $sPersona = StringMidEx($pngFileContent, 'aiPersona":"', '","basePrompt')
Global $sExample = StringMidEx($pngFileContent, ',"customDialogue":"', '","firstMessage":')
Global $sFirstMsg = StringMidEx($pngFileContent, ',"firstMessage":"', '","grammar"')

;replace {character} with {char} for tavern
$sPersona = StringReplace($sPersona,"{character}","{{char}}")
$sExample = StringReplace($sExample,"{character}","{{char}}")
$sFirstMsg = StringReplace($sFirstMsg,"{character}","{{char}}")
$sPersona = StringReplace($sPersona,"{user}","{{user}}")
$sExample = StringReplace($sExample,"{user}","{{user}}")
$sFirstMsg = StringReplace($sFirstMsg,"{user}","{{user}}")

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

Func _GetPNGExtraBase64Data($pngFilePath)
   Local $fileHandle = FileOpen($pngFilePath, $FO_READ + $FO_BINARY)
   ; Check if the file was opened successfully
   If $fileHandle = -1 Then
	   MsgBox($MB_OK + $MB_ICONERROR, "Error", "Unable to open the PNG file.")
	   Exit
   EndIf
   ; Read the PNG file content then close
   Local $pngFileContent = FileRead($fileHandle)
   FileClose($fileHandle)

   ; Convert binary content to a string for processing
   Local $pngFileString = BinaryToString($pngFileContent)

   ; Find the position of the ASCII marker
   Local $asciiMarker = "ASCII"
   Local $markerPos = StringInStr($pngFileString, $asciiMarker)

   If $markerPos = 0 Then
	   MsgBox($MB_OK + $MB_ICONERROR, "Error", "ASCII marker not found.")
	   Exit
   EndIf

   ; Extract the base64 data that follows the ASCII marker
   Local $startPos = $markerPos + StringLen($asciiMarker)
   Local $endPos = StringInStr($pngFileString, "Q==", 0, 1, $startPos)

   If $endPos = 0 Then
	   MsgBox($MB_OK + $MB_ICONERROR, "Error", "Ending 'Q==' not found.")
	   Exit
   EndIf

   Local $base64Data = StringMid($pngFileString, $startPos, $endPos - $startPos + 3) ; Include 'Q=='

   ; Clean up the base64 data by removing any non-base64 characters
   Local $cleanBase64Data = StringRegExpReplace($base64Data, "[^A-Za-z0-9+/=]", "")

   ; Display the base64 data in the console
   ;ConsoleWrite("Base64 Data: " & $cleanBase64Data & @CRLF)

   ; Optionally, decode the base64 data
   Local $decodedData = BinaryToString(base64($cleanBase64Data, False), 1)

   Return $decodedData
EndFunc

 ;==============================================================================================================================
; Function:         base64($vCode [, $bEncode = True [, $bUrl = False]])
;
; Description:      Decode or Encode $vData using Microsoft.XMLDOM to Base64Binary or Base64Url.
;                   IMPORTANT! Encoded base64url is without @LF after 72 lines. Some websites may require this.
;
; Parameter(s):     $vData      - string or integer | Data to encode or decode.
;                   $bEncode    - boolean           | True - encode, False - decode.
;                   $bUrl       - boolean           | True - output is will decoded or encoded using base64url shema.
;
; Return Value(s):  On Success - Returns output data
;                   On Failure - Returns 1 - Failed to create object.
;
; Author (s):       (Ghads on Wordpress.com), Ascer
;===============================================================================================================================
Func base64($vCode, $bEncode = True, $bUrl = False)

    Local $oDM = ObjCreate("Microsoft.XMLDOM")
    If Not IsObj($oDM) Then Return SetError(1, 0, 1)

    Local $oEL = $oDM.createElement("Tmp")
    $oEL.DataType = "bin.base64"

    If $bEncode then
        $oEL.NodeTypedValue = Binary($vCode)
        If Not $bUrl Then Return $oEL.Text
        Return StringReplace(StringReplace(StringReplace($oEL.Text, "+", "-"),"/", "_"), @LF, "")
    Else
        If $bUrl Then $vCode = StringReplace(StringReplace($vCode, "-", "+"), "_", "/")
        $oEL.Text = $vCode
        Return $oEL.NodeTypedValue
    EndIf

EndFunc ;==>base64
