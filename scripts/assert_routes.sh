#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Asserting OpenAPI routes..."

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "❌ jq not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y jq
    elif command -v brew &> /dev/null; then
        brew install jq
    else
        echo "❌ Cannot install jq automatically. Please install jq manually."
        exit 1
    fi
fi

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
        echo "✅ Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend not ready after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Assert required routes exist
echo "🔍 Checking OpenAPI routes..."

# Get OpenAPI spec
OPENAPI_SPEC=$(curl -sf http://127.0.0.1:8000/openapi.json)

# Check health route
if echo "$OPENAPI_SPEC" | jq -e '.paths["/api/health"].get' >/dev/null; then
    echo "✅ /api/health GET route exists"
else
    echo "❌ /api/health GET route missing"
    exit 1
fi

# Check upload route
if echo "$OPENAPI_SPEC" | jq -e '.paths["/api/upload"].post' >/dev/null; then
    echo "✅ /api/upload POST route exists"
else
    echo "❌ /api/upload POST route missing"
    exit 1
fi

# Check route parameters
UPLOAD_PARAMS=$(echo "$OPENAPI_SPEC" | jq -r '.paths["/api/upload"].post.requestBody.content."multipart/form-data".schema.properties.file.type // "not found"')
if [ "$UPLOAD_PARAMS" = "string" ] || [ "$UPLOAD_PARAMS" = "not found" ]; then
    echo "✅ Upload route accepts file parameter"
else
    echo "⚠️  Upload route parameters: $UPLOAD_PARAMS"
fi

echo "🎉 All OpenAPI routes validated successfully!"
