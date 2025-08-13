# OWLIN-App
Invoice auditing and supplier insights tool for hospitality

## Local LLM Parser (Sellable + Licensed)

OWLIN now includes a local, offline invoice/receipt parser that yields high-accuracy line-item tables and per-field confidence, including multi-page and multi-invoice PDFs and supermarket receipts.

### Local Model Setup

#### Option A (Default): Qwen2.5-VL via Ollama

1. Install Ollama:
```bash
brew install ollama  # macOS
# or visit https://ollama.ai for other platforms
```

2. Pull the Qwen2.5-VL model:
```bash
ollama pull qwen2.5-vl:latest
```

3. Set environment variables:
```bash
export LLM_BACKEND=qwen-vl
export MODEL_HOST_URL=http://localhost:11434
```

4. Start Ollama:
```bash
ollama serve
```

#### Option B (Optional): Llama 3.1 + Surya

1. Install Llama 3.1:
```bash
ollama pull llama3.1:8b
```

2. Install Surya:
```bash
pip install surya-ocr
```

3. Set environment variables:
```bash
export LLM_BACKEND=llama-surya
export MODEL_HOST_URL=http://localhost:11434
```

### Configuration

Add these environment variables to your `.env` file:

```bash
# LLM Configuration
LLM_BACKEND=qwen-vl                    # Default: qwen-vl
LOCAL_LLM_ENABLED=true                 # Default: true
MODEL_HOST_URL=http://localhost:11434  # Ollama default
```

### Features

- **High-accuracy line-item extraction** with confidence scores
- **Multi-page and multi-invoice PDF support**
- **Supermarket receipt parsing**
- **Local processing** - no data leaves your device
- **OCR fallback** when LLM is unavailable
- **Comprehensive validation** with warnings for anomalies

### Compliance & Licensing

- **Qwen2.5-VL**: Apache-2.0 License
- **Llama 3.1**: Llama Community License (optional)
- **Surya**: Apache-2.0 License (optional)

See `THIRD_PARTY_LICENSES/` for full license texts.

## Improved OCR Pipeline

This update introduces an optional module `backend/ocr_pipeline.py` which preprocesses images (grayscale, deskew, threshold, noise reduction) before running Tesseract with a tuned configuration. The module provides `parse_document()` returning structured line items, totals and a confidence score with a flag for low-confidence results.
