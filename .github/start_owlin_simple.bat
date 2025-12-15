@echo off
cd /d "C:\Users\tedev\Desktop\owlin_backup_2025-10-02_225554\source_extracted"
set OWLIN_ENV=dev
set OWLIN_DB_PATH=C:\Users\tedev\Desktop\owlin_backup_2025-10-02_225554\data\owlin.db
set OWLIN_UPLOADS_DIR=C:\Users\tedev\Desktop\owlin_backup_2025-10-02_225554\data\uploads
set OWLIN_DEMO=0
set OWLIN_DEFAULT_VENUE=Royal Oak Hotel
set OWLIN_SINGLE_PORT=1
echo Starting Owlin...
python test_backend_simple.py
