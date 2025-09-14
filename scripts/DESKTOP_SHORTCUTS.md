# 🖥️ OWLIN Desktop Shortcuts

## Double-Click to Launch

### Windows
- **`launch_owlin_dev.bat`** - Command Prompt launcher
- **`launch_owlin_dev.ps1`** - PowerShell launcher (right-click → "Run with PowerShell")

### macOS/Linux  
- **`launch_owlin_dev.sh`** - Terminal launcher

## What They Do

1. **Check** you're in the right directory
2. **Start Next.js** in a new terminal window (port 3000)
3. **Start FastAPI** in a new terminal window (port 8001) 
4. **Open browser** to http://127.0.0.1:8001
5. **Show status** and wait for you to press Enter

## Features

- ✅ **Auto-detects** your OS and uses appropriate terminal
- ✅ **Opens browser** automatically
- ✅ **Separate windows** for each service (easy to monitor)
- ✅ **Error checking** (validates you're in the right directory)
- ✅ **Cross-platform** (Windows, macOS, Linux)

## Usage

1. **Navigate** to the Owlin project root
2. **Double-click** the appropriate launcher for your OS
3. **Wait** for both services to start (5-10 seconds)
4. **Use the app** at http://127.0.0.1:8001
5. **Close terminal windows** to stop services

## Troubleshooting

- **"package.json not found"**: Run from the Owlin project root directory
- **Services won't start**: Check that Node.js and Python are installed
- **Port conflicts**: Close any existing services on ports 3000/8001
- **Permission denied** (Linux/macOS): Run `chmod +x scripts/launch_owlin_dev.sh`

---

**Result**: One double-click launches your entire Owlin development environment! 🚀
