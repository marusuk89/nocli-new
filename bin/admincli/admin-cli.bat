@echo off

set DIR=%~dp0
set NODE=%DIR%\node\windows\bin\node.exe
set MAIN_SCRIPT=%DIR%\bin\main.bundle.js
set FLAG_EXPOSE_GC="--expose_gc"
set FLAG_NO_WARNINGS="--no-warnings"

"%NODE%" %FLAG_EXPOSE_GC% %FLAG_NO_WARNINGS% "%MAIN_SCRIPT%" %*
