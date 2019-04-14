@ECHO OFF
CALL activate MovieCompressor

REM if no parameters are passed, pass current directory to script
REM %* will return the remainder of the command line starting at the first command line argument
REM %CD% returns the current directory
IF "%*"=="" (SET params="%CD%")ELSE (SET params="%*")

REM ECHO 1 rest: %*
REM Echo 2 CD: %CD%
REM ECHO 3 params: %params%

python f:\Libraries\Pesche\Docs_Pesche\Coding\Python\MovieCompressor\MovieCompressor.py %params%
CALL conda deactivate
REM PAUSE
