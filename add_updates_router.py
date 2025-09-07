#!/usr/bin/env python3
import re

# Read the file
with open('backend/main_fixed.py', 'r') as f:
    content = f.read()

# Add the import after document queue routes
import_pattern = r'(# Import document queue routes.*?except ImportError:.*?@document_queue_router\.get\("/queue"\).*?return {"documents": \[\]})'
replacement = r'''# Import document queue routes
try:
    from routes.document_queue import router as document_queue_router
except ImportError:
    # If document queue routes aren't available, create a dummy router
    from fastapi import APIRouter
    document_queue_router = APIRouter(prefix="/documents", tags=["documents"])
    
    @document_queue_router.get("/queue")
    async def get_documents_for_review():
        return {"documents": []}

# Import updates routes
try:
    from routes.updates import router as updates_router
except ImportError:
    # If updates routes are not available, create a dummy router
    from fastapi import APIRouter
    updates_router = APIRouter(prefix="/updates", tags=["updates"])
    
    @updates_router.get("/available")
    async def get_available_updates():
        return {"updates": []}'''

content = re.sub(import_pattern, replacement, content, flags=re.DOTALL)

# Add the router include after document queue router include
include_pattern = r'(app\.include_router\(document_queue_router, prefix="/api"\))'
replacement = r'\1\n\n# Include updates routes\napp.include_router(updates_router, prefix="/api")'

content = re.sub(include_pattern, replacement, content)

# Write the file back
with open('backend/main_fixed.py', 'w') as f:
    f.write(content)

print("Updated main_fixed.py with updates router")
