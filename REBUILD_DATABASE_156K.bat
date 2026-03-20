@echo off
echo ================================================================================
echo REBUILD DATABASE WITH ALL 156K DOCUMENTS
echo ================================================================================
echo.
echo This will:
echo   1. Backup existing database (if exists)
echo   2. Load ALL 156K documents (Kanoon.com loaded fully)
echo   3. Create new hybrid search database
echo   4. Test the new database
echo.
echo Estimated time: 30-40 minutes
echo.
echo ================================================================================
echo.
pause

python rebuild_database_156K.py

echo.
echo ================================================================================
echo DONE!
echo ================================================================================
pause

