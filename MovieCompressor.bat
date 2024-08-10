@ECHO OFF
CALL activate MovieCompressor
REM Enabling colors https://www.dostips.com/forum/viewtopic.php?t=1707
SETLOCAL DisableDelayedExpansion
REM Disables delayed environment variable expansion, which affects how variables are interpreted within the loop.
REM This loop sets the DEL variable to a special control character that allows for colored output in the command prompt.
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
  set "DEL=%%a"
)

call :ColorText 0e "Paths with spaces must be enclosed in quotation marks"
call :ColorText 0e "and must NOT end with a backslash!"
REM blank line:
ECHO(


REM if no parameters are passed, pass current directory to script
REM %* will return the remainder of the command line starting at the first command line argument
REM %CD% returns the current directory
REM IF "%*" == "" does not work if the path contains spaces and has to be quoted. [%*] still does not work.
REM Resorted to IF NOT DEFINED

REM Stores the first argument passed to the script
SET firstParam=%1
REM ~ removes any surrounding quotes from the first parameter 
SET firstParamWithoutQuotes=%~1

REM set starChars to XX if empty to avoid downstream syntax errors
REM if not empty, extract the first char to check downstream if it is a dash (~: substring operation, 0,1: extract substring starting at pos 0, length 1)
IF NOT DEFINED firstParamWithoutQuotes (
    SET startChars=XX
) ELSE (
    SET startChars=%firstParamWithoutQuotes:~0,1%
)

REM If no parameter is passed, pass the current directory as only parameter
REM If the first character of the first parameter is a dash (-), assume the parameter is a flag and append the current directory in front of the parameters (%%)
REM Otherwise, simply uses the parameters as they are
IF NOT DEFINED firstParam (
    SET params="%CD%"
) ELSE (
    IF %startChars% == - (
        SET params="%CD%" %*
    ) ELSE (
        SET params=%*
    )
)
ECHO Passed parameters:
ECHO %params%

REM ECHO 1 rest: %*
REM Echo 2 CD: %CD%
REM ECHO 3 params: %params%

python f:\Libraries\Pesche\Docs_Pesche\Coding\Python\MovieCompressor\MovieCompressor.py %params%
CALL conda deactivate
REM PAUSE
goto :eof

:ColorText
echo off
<nul set /p .=. > "%~2"
findstr /v /a:%1 /R "^$" "%~2" nul
echo(%DEL%%DEL%%DEL%
del "%~2" > nul 2>&1
goto :eof