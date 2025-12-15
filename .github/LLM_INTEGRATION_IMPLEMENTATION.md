# Local LLM Integration for Advanced Interpretation & Automation

## Overview

This document describes the implementation of a comprehensive local LLM integration system for the OCR pipeline, enabling advanced interpretation and automation features while maintaining full offline operation.

## Features

- **Local LLM Inference**: Quantized models (GGUF format) running offline
- **Invoice Card Generation**: LLM-powered conversion of OCR artifacts to standardized invoice cards
- **Credit Request Automation**: Automatic email drafting for anomalies and credit requests
- **Post-Correction Engine**: LLM-powered correction of uncertain normalizations
- **Anomaly Detection**: Intelligent detection of invoice anomalies and issues
- **Complete Integration**: Seamless integration with existing OCR and confidence routing system

## Architecture

### Core Components

1. **LocalLLMInterface**: Unified interface for local LLM inference
2. **InvoiceCardGenerator**: LLM-powered invoice card generation
3. **AutomationFeatures**: Credit requests, post-correction, and anomaly detection
4. **LLMPipeline**: Complete LLM processing pipeline
5. **OCRLLMIntegration**: Integration with existing OCR pipeline

### Data Flow

```
OCR Data → Confidence Routing → LLM Processing → Invoice Card + Automation Artifacts
```

## Installation

### Prerequisites

```bash
# Install required dependencies
pip install llama-cpp-python
pip install torch  # Optional, for GPU support
pip install transformers  # Optional, for additional model support
```

### Model Setup

1. **Download Quantized Models**:
   ```bash
   # Create models directory
   mkdir -p models
   
   # Download Llama 2 7B Chat (Q4_K_M quantization)
   wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf -O models/llama-2-7b-chat.Q4_K_M.gguf
   
   # Alternative: Mistral 7B (smaller, faster)
   wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf -O models/mistral-7b-instruct-v0.1.Q4_K_M.gguf
   ```

2. **Configure Model Paths**:
   ```python
   from backend.llm.local_llm import LLMConfig, LLMProvider, LLMDevice
   
   config = LLMConfig(
       model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
       provider=LLMProvider.LLAMA_CPP,
       device=LLMDevice.AUTO,
       max_tokens=2048,
       temperature=0.0,  # Deterministic output
       n_threads=4
   )
   ```

### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ for 7B models
- **Storage**: 4GB+ for quantized models
- **GPU**: Optional, for faster inference

## Usage

### Basic Usage

```python
from backend.llm.ocr_llm_integration import OCRLLMIntegration
from backend.llm.local_llm import LLMConfig, LLMProvider, LLMDevice

# Initialize with LLM configuration
llm_config = LLMConfig(
    model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
    provider=LLMProvider.LLAMA_CPP,
    device=LLMDevice.AUTO
)

integration = OCRLLMIntegration([llm_config])

# Process document
raw_ocr_data = {
    "supplier": "ACME Corporation Ltd",
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "currency": "GBP",
    "subtotal": "£100.00",
    "tax_amount": "£20.00",
    "total_amount": "£120.00",
    "line_items": [...]
}

context = {
    "invoice_id": "invoice-001",
    "region": "UK",
    "known_suppliers": ["ACME Corporation Ltd"],
    "default_currency": "GBP"
}

result = integration.process_document(
    raw_ocr_data=raw_ocr_data,
    context=context,
    enable_llm_processing=True,
    enable_automation=True
)

# Access results
print(f"Success: {result.success}")
print(f"Processing time: {result.total_processing_time:.3f}s")
print(f"Final invoice card: {result.final_invoice_card}")
print(f"Review queue: {len(result.review_queue)} items")
print(f"Automation artifacts: {result.automation_artifacts}")
```

### Advanced Configuration

```python
# Multiple LLM configurations with fallback
llm_configs = [
    LLMConfig(
        model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
        provider=LLMProvider.LLAMA_CPP,
        device=LLMDevice.GPU,
        n_gpu_layers=-1  # All layers on GPU
    ),
    LLMConfig(
        model_path="models/mistral-7b-instruct-v0.1.Q4_K_M.gguf",
        provider=LLMProvider.LLAMA_CPP,
        device=LLMDevice.CPU,
        n_threads=8
    )
]

integration = OCRLLMIntegration(llm_configs)
```

### Batch Processing

```python
# Process multiple documents
batch_data = [
    {
        "raw_ocr_data": {...},
        "context": {...}
    },
    # ... more documents
]

results = integration.batch_process_documents(
    batch_data=batch_data,
    enable_llm_processing=True,
    enable_automation=True
)

# Get statistics
stats = integration.get_integration_stats(results)
print(f"Processed {stats['total_documents']} documents")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Average processing time: {stats['average_processing_time']:.3f}s")
```

## LLM Components

### LocalLLMInterface

```python
from backend.llm.local_llm import LocalLLMInterface, LLMConfig

# Initialize LLM interface
config = LLMConfig(
    model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
    provider=LLMProvider.LLAMA_CPP,
    device=LLMDevice.AUTO
)

llm = LocalLLMInterface(config)

# Generate text
result = llm.generate("Generate an invoice card for ACME Corp")
print(f"Generated: {result.text}")
print(f"Tokens: {result.tokens_generated}")
print(f"Time: {result.inference_time:.3f}s")
```

### InvoiceCardGenerator

```python
from backend.llm.invoice_card_generator import InvoiceCardGenerator

generator = InvoiceCardGenerator(llm)

result = generator.generate_invoice_card(
    ocr_data=ocr_data,
    confidence_scores=confidence_scores,
    review_candidates=review_candidates
)

print(f"Invoice card: {result.invoice_card.to_dict()}")
```

### Automation Features

```python
from backend.llm.automation_features import CreditRequestGenerator, PostCorrectionEngine, AnomalyDetector

# Credit request generation
credit_generator = CreditRequestGenerator(llm)
credit_request = credit_generator.generate_credit_request(
    invoice_data=invoice_data,
    anomalies=["Duplicate charge"],
    credit_reasons=["Already paid"]
)

# Post-correction
correction_engine = PostCorrectionEngine(llm)
correction = correction_engine.correct_data(
    original_data=original_data,
    confidence_issues=["Date format unclear"]
)

# Anomaly detection
anomaly_detector = AnomalyDetector(llm)
anomalies = anomaly_detector.detect_anomalies(invoice_data)
```

## Prompt Templates

### Custom Prompt Templates

```python
from backend.llm.prompt_templates import PromptTemplates, PromptTemplate, PromptType

templates = PromptTemplates()

# Add custom template
custom_template = PromptTemplate(
    name="custom_invoice_processing",
    prompt_type=PromptType.INVOICE_CARD,
    template="Your custom prompt template here...",
    examples=[...],
    schema={...}
)

templates.add_custom_template(custom_template)
```

### Available Prompt Types

- **INVOICE_CARD**: Generate standardized invoice cards
- **CREDIT_REQUEST**: Draft credit request emails
- **POST_CORRECTION**: Correct uncertain normalizations
- **REVIEW_SUGGESTION**: Provide review suggestions

## Performance Optimization

### Model Selection

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| Llama 2 7B | 4GB | Medium | High | Production |
| Mistral 7B | 4GB | Fast | High | Development |
| Llama 2 13B | 8GB | Slow | Very High | High-quality |

### Configuration Tuning

```python
# Fast inference (lower quality)
config = LLMConfig(
    max_tokens=1024,
    temperature=0.0,
    n_threads=8,
    n_gpu_layers=0  # CPU only
)

# High quality (slower)
config = LLMConfig(
    max_tokens=2048,
    temperature=0.1,
    n_threads=4,
    n_gpu_layers=-1  # All layers on GPU
)
```

### Batch Processing

```python
# Process multiple documents efficiently
results = integration.batch_process_documents(
    batch_data=batch_data,
    enable_llm_processing=True,
    enable_automation=True
)

# Get performance statistics
stats = integration.get_integration_stats(results)
print(f"Total time: {stats['total_processing_time']:.3f}s")
print(f"Average per document: {stats['average_processing_time']:.3f}s")
```

## Testing and Validation

### Run Validation Script

```bash
# Run comprehensive validation
python backend/llm/validate_llm_system.py

# Run specific tests
python -m pytest tests/test_llm_integration.py -v
```

### Performance Benchmarking

```python
# Benchmark inference time
import time

start_time = time.time()
result = integration.process_document(raw_ocr_data)
end_time = time.time()

print(f"Processing time: {end_time - start_time:.3f}s")
print(f"LLM time: {result.llm_pipeline_result.processing_time:.3f}s")
```

### Offline Operation Validation

```python
# Ensure offline operation
config = LLMConfig(
    model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
    provider=LLMProvider.LLAMA_CPP,
    device=LLMDevice.CPU  # Force CPU for offline
)

integration = OCRLLMIntegration([config])

# Test without network
result = integration.process_document(raw_ocr_data)
assert result.llm_pipeline_result.llm_result.provider == "llama_cpp"
```

## Error Handling

### LLM Inference Failures

```python
try:
    result = integration.process_document(raw_ocr_data)
    if not result.success:
        print(f"Processing failed: {result.errors}")
except Exception as e:
    print(f"Integration error: {e}")
```

### Fallback Mechanisms

```python
# Multiple LLM configurations with fallback
llm_configs = [
    LLMConfig(model_path="models/llama-2-7b-chat.Q4_K_M.gguf", provider=LLMProvider.LLAMA_CPP),
    LLMConfig(model_path="models/mistral-7b-instruct-v0.1.Q4_K_M.gguf", provider=LLMProvider.LLAMA_CPP),
    LLMConfig(model_path="mock", provider=LLMProvider.MOCK)  # Fallback
]

integration = OCRLLMIntegration(llm_configs)
```

### Graceful Degradation

```python
# Process with LLM disabled if needed
result = integration.process_document(
    raw_ocr_data=raw_ocr_data,
    enable_llm_processing=False  # Use OCR results only
)
```

## Monitoring and Logging

### Logging Configuration

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# LLM-specific logging
logger = logging.getLogger("owlin.llm")
logger.setLevel(logging.DEBUG)
```

### Performance Monitoring

```python
# Monitor processing times
result = integration.process_document(raw_ocr_data)

print(f"Total time: {result.total_processing_time:.3f}s")
print(f"OCR time: {result.confidence_routing_result.processing_time:.3f}s")
print(f"LLM time: {result.llm_pipeline_result.processing_time:.3f}s")
print(f"LLM efficiency: {result.llm_pipeline_result.processing_time / result.total_processing_time:.1%}")
```

### Audit Logging

```python
# All LLM actions are logged
# Check logs for:
# - Model loading and initialization
# - Inference requests and responses
# - Processing times and performance
# - Error conditions and fallbacks
```

## Troubleshooting

### Common Issues

1. **Model Loading Failures**:
   ```bash
   # Check model file exists
   ls -la models/llama-2-7b-chat.Q4_K_M.gguf
   
   # Check file permissions
   chmod 644 models/llama-2-7b-chat.Q4_K_M.gguf
   ```

2. **Memory Issues**:
   ```python
   # Reduce model size or use CPU
   config = LLMConfig(
       model_path="models/mistral-7b-instruct-v0.1.Q4_K_M.gguf",  # Smaller model
       n_gpu_layers=0,  # CPU only
       n_threads=2  # Fewer threads
   )
   ```

3. **Slow Inference**:
   ```python
   # Use GPU if available
   config = LLMConfig(
       n_gpu_layers=-1,  # All layers on GPU
       n_threads=8  # More CPU threads
   )
   ```

### Debug Mode

```python
# Enable debug logging
config = LLMConfig(
    verbose=True,  # Enable verbose output
    model_path="models/llama-2-7b-chat.Q4_K_M.gguf"
)

# Check system validation
validation = integration.validate_integration()
print(f"Integration ready: {validation['integration_ready']}")
```

## Future Enhancements

### Planned Features

1. **Model Fine-tuning**: Custom models for specific document types
2. **Multi-language Support**: Support for non-English documents
3. **Advanced Prompting**: Few-shot learning and prompt optimization
4. **Real-time Processing**: Streaming inference for large documents

### Integration Opportunities

1. **Workflow Automation**: Integration with business process management
2. **Quality Assurance**: Automated testing and validation
3. **Analytics**: Business intelligence on document processing
4. **Compliance**: Audit trails for regulatory requirements

## Conclusion

The local LLM integration system provides a robust foundation for advanced invoice processing with intelligent interpretation and automation. It ensures high accuracy while maintaining full offline operation and providing comprehensive automation features.

The system is designed for scalability, maintainability, and integration with existing workflows, providing a solid foundation for production invoice processing systems with advanced AI capabilities.
