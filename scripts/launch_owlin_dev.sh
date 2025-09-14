#!/bin/bash
# OWLIN - Desktop Launcher for macOS/Linux
# Double-click this file to start the full Owlin development environment

echo ""
echo "========================================"
echo "  OWLIN - Full Development Launcher"
echo "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "ERROR: package.json not found!"
    echo "Please run this from the Owlin project root directory."
    read -p "Press Enter to continue..."
    exit 1
fi

if [ ! -f "backend/final_single_port.py" ]; then
    echo "ERROR: backend/final_single_port.py not found!"
    echo "Please run this from the Owlin project root directory."
    read -p "Press Enter to continue..."
    exit 1
fi

echo "Starting Owlin development environment..."
echo ""

# Start Next.js in a new terminal window
echo "[1/2] Starting Next.js frontend..."
if command -v osascript &> /dev/null; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && npm run dev"'
elif command -v gnome-terminal &> /dev/null; then
    # Linux with GNOME Terminal
    gnome-terminal -- bash -c "cd '$(pwd)' && npm run dev; exec bash"
elif command -v xterm &> /dev/null; then
    # Linux with xterm
    xterm -e "cd '$(pwd)' && npm run dev" &
else
    # Fallback - run in background
    npm run dev &
fi

# Wait a moment for Next.js to start
sleep 5

# Start FastAPI backend in a new terminal window
echo "[2/2] Starting FastAPI backend with proxy..."
if command -v osascript &> /dev/null; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && UI_MODE=PROXY_NEXT NEXT_BASE=http://127.0.0.1:3000 LLM_BASE=http://127.0.0.1:11434 OWLIN_PORT=8001 python -m backend.final_single_port"'
elif command -v gnome-terminal &> /dev/null; then
    # Linux with GNOME Terminal
    gnome-terminal -- bash -c "cd '$(pwd)' && UI_MODE=PROXY_NEXT NEXT_BASE=http://127.0.0.1:3000 LLM_BASE=http://127.0.0.1:11434 OWLIN_PORT=8001 python -m backend.final_single_port; exec bash"
elif command -v xterm &> /dev/null; then
    # Linux with xterm
    xterm -e "cd '$(pwd)' && UI_MODE=PROXY_NEXT NEXT_BASE=http://127.0.0.1:3000 LLM_BASE=http://127.0.0.1:11434 OWLIN_PORT=8001 python -m backend.final_single_port" &
else
    # Fallback - run in background
    UI_MODE=PROXY_NEXT NEXT_BASE=http://127.0.0.1:3000 LLM_BASE=http://127.0.0.1:11434 OWLIN_PORT=8001 python -m backend.final_single_port &
fi

# Wait a moment for backend to start
sleep 3

echo ""
echo "========================================"
echo "  SUCCESS! Owlin is starting up..."
echo "========================================"
echo ""
echo "Frontend: http://127.0.0.1:3000"
echo "Backend:  http://127.0.0.1:8001"
echo ""
echo "Opening the app in your browser..."
echo ""

# Open the app in the default browser
if command -v open &> /dev/null; then
    # macOS
    open http://127.0.0.1:8001
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://127.0.0.1:8001
else
    echo "Please open http://127.0.0.1:8001 in your browser"
fi

echo ""
echo "Both services are starting in separate terminal windows."
echo "Close those windows to stop the services."
echo ""
read -p "Press Enter to close this launcher..."
