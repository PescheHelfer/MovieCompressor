@ECHO OFF
CALL activate MovieCompressor
REM Enabling colors https://www.dostips.com/forum/viewtopic.php?t=1707
SETLOCAL DisableDelayedExpansion
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


SET firstParam=%1
SET firstParamWithoutQuotes=%~1

REM set starChars to XX if empty to avoid downstream syntax errors
REM if not empty, extract the first char to check downstream if it is a dash
IF NOT DEFINED firstParamWithoutQuotes (
    SET startChars=XX
) ELSE (
    SET startChars=%firstParamWithoutQuotes:~0,1%
)

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