@echo off

set DIR=%~dp0
set NODE=%DIR%\node\windows\bin\node.exe
set MAIN_SCRIPT=%DIR%\bin\agent.bundle.js
set FLAGS="--expose_gc"

%NODE% %FLAGS% %MAIN_SCRIPT% %*
