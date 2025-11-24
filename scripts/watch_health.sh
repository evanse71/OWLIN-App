#!/bin/bash
# Health watchdog script for OWLIN pairing MVP
# Usage: Add to cron or systemd timer to monitor health endpoint

set -e

# Configuration
HEALTH_URL="http://127.0.0.1:8000/api/health"
TIMEOUT=10
LOG_FILE="data/logs/health_watch.log"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log_with_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

# Check if server is responding
check_health() {
    local response
    local status
    
    # Get health response with timeout
    response=$(curl -s --max-time "$TIMEOUT" "$HEALTH_URL" 2>/dev/null || echo "ERROR")
    
    if [ "$response" = "ERROR" ]; then
        log_with_timestamp "HEALTH_CHECK_FAILED: Server not responding"
        return 1
    fi
    
    # Check if response contains "ok" status
    status=$(echo "$response" | jq -r '.status' 2>/dev/null || echo "ERROR")
    
    if [ "$status" = "ok" ]; then
        log_with_timestamp "HEALTH_CHECK_PASSED: Server healthy"
        return 0
    else
        log_with_timestamp "HEALTH_CHECK_FAILED: Status=$status, Response=$response"
        return 1
    fi
}

# Main health check
if check_health; then
    exit 0
else
    exit 1
fi