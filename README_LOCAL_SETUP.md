# Owlin — Local Dev Rebuild (From Zero)

## 0) Clone (never download HTML)
```bash
git clone https://github.com/evanse71/OWLIN-App.git
cd OWLIN-App
```

## 1) System prerequisites

**macOS (Homebrew)**

```bash
brew update
brew install tesseract poppler python@3.11 node
```

**Ubuntu/Debian**

```bash
sudo apt update
sudo apt install -y tesseract-ocr libtesseract-dev poppler-utils python3.11 python3.11-venv nodejs npm
```

**Windows**

* Install Tesseract (add to PATH)
* Install Poppler (add `bin` to PATH)
* Install Python 3.11 (Add to PATH)
* Install Node.js LTS

## 2) One-shot bootstrap

**macOS/Linux**

```bash
chmod +x scripts/bootstrap_mac_linux.sh
./scripts/bootstrap_mac_linux.sh
```

**Windows (PowerShell)**

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\bootstrap_windows.ps1
```

## 3) Verify

* Backend: [http://localhost:8001/health](http://localhost:8001/health) → `{"status":"ok"}`
* Docs: [http://localhost:8001/docs](http://localhost:8001/docs)
* Frontend: [http://localhost:3000](http://localhost:3000)

## 4) Env files

* `backend/.env` from `.env.example`
* `frontend/.env.local` from `.env.example`

## 5) Troubleshooting

```bash
# free ports
lsof -ti :3000 | xargs kill -9
lsof -ti :8001 | xargs kill -9
# verify Tesseract
tesseract --version
# verify Poppler
pdftoppm -v
```
