# Owlin App - Lovable UI Implementation

This project has been updated with the Lovable UI design system, replacing the previous Next.js implementation with a modern React + Vite setup.

## Features

- **Modern UI**: Clean, professional interface using Lovable design tokens
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Processing**: OCR processing with job polling
- **Invoice Management**: Upload, edit, and manage invoices
- **Delivery Note Pairing**: Match delivery notes with invoices
- **Backend Integration**: FastAPI + SQLite backend for data persistence

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **UI Components**: Custom components with Tailwind CSS
- **Backend**: FastAPI + SQLite
- **OCR**: Tesseract via pytesseract
- **Styling**: Tailwind CSS with custom design tokens

## Quick Start

### Backend Setup

```bash
cd backend
pip install fastapi uvicorn[standard] pytesseract opencv-python
python3 -m uvicorn app:app --reload --port 8001
```

### Frontend Setup

```bash
npm install
VITE_USE_FAKE_BACKEND=false npm run dev
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8001

## Project Structure

```
src/
├── components/          # UI components
│   ├── layout/         # Layout components (Sidebar, etc.)
│   ├── ui/            # Base UI components (Button, Card, etc.)
│   └── invoices/      # Invoice-specific components
├── hooks/             # Custom React hooks
├── lib/               # Utilities and API clients
├── pages/             # Page components
└── types.ts           # TypeScript type definitions
```

## Key Features

### Invoice Management
- Upload documents for OCR processing
- View processing progress with real-time updates
- Edit invoice details and line items
- Confidence scoring for OCR results

### Delivery Note Pairing
- View unmatched delivery notes
- Pair delivery notes with invoices
- Compare delivery notes and invoices for discrepancies

### Modern UI
- Collapsible sidebar navigation
- Responsive design with mobile support
- Toast notifications for user feedback
- Clean, professional styling

## API Endpoints

- `GET /invoices` - List all invoices
- `GET /invoices/{id}` - Get specific invoice details
- `POST /upload` - Upload document for OCR processing
- `GET /jobs/{job_id}` - Get job status
- `GET /delivery-notes/unmatched` - Get unmatched delivery notes
- `POST /pair` - Pair delivery note with invoice
- `POST /submit` - Submit documents to Owlin

## Development

The project uses:
- **Vite** for fast development and building
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **React Router** for navigation
- **FastAPI** for the backend API

## Design System

The UI follows the Lovable design system with:
- Consistent spacing and typography
- Professional color palette
- Accessible component design
- Responsive layouts
