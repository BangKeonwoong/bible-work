@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "PYTHONPATH=%ROOT_DIR%src;%PYTHONPATH%"

where python >NUL 2>&1
if %ERRORLEVEL%==0 (
  python -m bhs_hierarchy.gui
  exit /b %ERRORLEVEL%
)

py -m bhs_hierarchy.gui
exit /b %ERRORLEVEL%
