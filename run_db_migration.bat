@echo off
echo ========================================
echo Owlin Database Migration
echo ========================================
echo.
echo Running database initialization...
echo.

python -c "from backend.app.db import init_db; init_db(); print('')"
python -c "print('Database initialized successfully!')"
python -c "print('')"
python -c "print('Verifying schema...')"
python scripts\debug_db_schema.py

echo.
echo ========================================
echo Migration Complete!
echo ========================================
pause

