#!/usr/bin/env python3
import re

# Read the file
with open('backend/main_fixed.py', 'r') as f:
    content = f.read()

# Add the import after updates routes
import_pattern = r'(# Import updates routes.*?@updates_router\.get\("/available"\).*?return {"updates": \[\]})'
replacement = r'''# Import updates routes
try:
    from routes.updates import router as updates_router
except ImportError:
    # If updates routes are not available, create a dummy router
    from fastapi import APIRouter
    updates_router = APIRouter(prefix="/updates", tags=["updates"])
    
    @updates_router.get("/available")
    async def get_available_updates():
        return {"updates": []}

# Import backup routes
try:
    from routes.backups import router as backups_router
except ImportError:
    # If backup routes are not available, create a dummy router
    from fastapi import APIRouter
    backups_router = APIRouter(prefix="/backups", tags=["backups"])
    
    @backups_router.get("")
    async def list_backups():
        return {"backups": []}

# Import support pack routes
try:
    from routes.support_packs import router as support_packs_router
except ImportError:
    # If support pack routes are not available, create a dummy router
    from fastapi import APIRouter
    support_packs_router = APIRouter(prefix="/support-packs", tags=["support-packs"])
    
    @support_packs_router.get("")
    async def list_support_packs():
        return {"support_packs": []}'''

content = re.sub(import_pattern, replacement, content, flags=re.DOTALL)

# Add the router includes after updates router include
include_pattern = r'(app\.include_router\(updates_router, prefix="/api"\))'
replacement = r'\1\n\n# Include backup routes\napp.include_router(backups_router, prefix="/api")\n\n# Include support pack routes\napp.include_router(support_packs_router, prefix="/api")'

content = re.sub(include_pattern, replacement, content)

# Write the file back
with open('backend/main_fixed.py', 'w') as f:
    f.write(content)

print("Updated main_fixed.py with backup and support pack routes")
