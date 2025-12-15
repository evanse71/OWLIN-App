# 🦉 OWLIN Troubleshooting Guide

## 🐛 White Screen Issue

If you're seeing a white screen at http://127.0.0.1:8000/, try these solutions:

### 1. **Clear Browser Cache**
- Press `Ctrl + F5` to hard refresh
- Or press `F12` → Right-click refresh button → "Empty Cache and Hard Reload"
- Or clear browser cache manually

### 2. **Check Browser Console**
- Press `F12` to open Developer Tools
- Go to the "Console" tab
- Look for any red error messages
- Common errors:
  - `Failed to fetch` - API connection issue
  - `CORS error` - Cross-origin request blocked
  - `Module not found` - JavaScript loading issue

### 3. **Verify Backend is Running**
```bash
curl http://127.0.0.1:8000/api/health
```
Should return: `{"status":"ok","version":"0.1.0-rc1","sha":"dev"}`

### 4. **Check Network Tab**
- Press `F12` → "Network" tab
- Refresh the page
- Look for failed requests (red entries)
- Check if `/assets/index-*.js` and `/assets/index-*.css` are loading

### 5. **Try Different Browser**
- Test in Chrome, Firefox, or Edge
- Disable browser extensions temporarily

### 6. **Restart Everything**
```bash
# Stop all processes
.\stop_owlin.bat

# Wait 5 seconds, then restart
.\start_owlin.bat
```

### 7. **Check File Permissions**
- Ensure the `data/` directory is writable
- Check that `source_extracted/tmp_lovable/dist/` exists

## 🔧 Common Issues

### Backend Won't Start
- **Port 8000 in use**: `netstat -ano | findstr :8000`
- **Kill process**: `taskkill /PID <pid> /F`
- **Python not found**: Install Python 3.8+ and add to PATH

### Frontend Build Fails
- **Node.js not installed**: Install Node.js 16+
- **npm not found**: Install npm or use Node.js installer
- **Dependencies missing**: Run `npm install` in `source_extracted/tmp_lovable/`

### API Connection Issues
- **CORS errors**: Backend is configured for localhost:3000, localhost:5173, localhost:8000
- **Network issues**: Check Windows Firewall
- **Wrong port**: Ensure backend is on port 8000

## 📋 Quick Health Check

Run these commands to verify everything is working:

```bash
# 1. Check if backend is running
curl http://127.0.0.1:8000/api/health

# 2. Check if frontend HTML is served
curl http://127.0.0.1:8000/

# 3. Check if JavaScript assets are served
curl -I http://127.0.0.1:8000/assets/index-*.js

# 4. Check if CSS assets are served
curl -I http://127.0.0.1:8000/assets/index-*.css
```

## 🆘 Still Having Issues?

1. **Check the backend window** for error messages
2. **Look at the logs** in `data/logs/app.log`
3. **Try split mode**: `.\start_owlin_split.bat`
4. **Check system requirements**:
   - Python 3.8+
   - Node.js 16+
   - Windows 10/11

## 📞 Getting Help

If you're still stuck:
1. Take a screenshot of the browser console (F12)
2. Copy any error messages from the backend window
3. Check the `data/logs/app.log` file for errors
4. Try the split mode launcher instead
