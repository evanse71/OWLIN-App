# Confidence Routing and Human-in-the-Loop Flagging System

## Overview

This document describes the implementation of a comprehensive confidence routing and human-in-the-loop flagging system for the OCR pipeline. The system ensures only high-confidence, error-free records are auto-accepted while routing questionable items for human review.

## Features

- **Per-field, per-block, and per-page confidence calculation** based on OCR model output, normalization success, and error metrics
- **Configurable confidence thresholds** with field-specific settings
- **Auto-accept vs. needs-review routing** with transparent decision making
- **Comprehensive audit logging** for all routing decisions
- **Error case handling** with graceful degradation
- **Review candidate collation** for rapid UI display
- **Cross-validation and context matching** for improved accuracy

## Architecture

### Core Components

1. **ConfidenceCalculator**: Calculates confidence metrics for fields, line items, and invoices
2. **ConfidenceRouter**: Routes items based on confidence scores and thresholds
3. **FieldNormalizer**: Integrated with confidence routing for end-to-end processing
4. **ReviewCandidate**: Represents items that need human review
5. **ConfidenceRoutingResult**: Complete result of routing decisions

### Data Flow

```
Raw OCR Data → Field Normalization → Confidence Calculation → Routing Decision → Review Candidates
```

## Usage

### Basic Usage

```python
from backend.normalization import FieldNormalizer

# Initialize with default configuration
normalizer = FieldNormalizer()

# Process invoice with confidence routing
raw_data = {
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

# Normalize with confidence routing
normalization_result, routing_result = normalizer.normalize_invoice_with_routing(raw_data, context)

# Check results
print(f"Overall confidence: {routing_result.overall_confidence}")
print(f"Auto-accepted fields: {routing_result.auto_accepted_fields}")
print(f"Review candidates: {len(routing_result.review_candidates)}")
```

### Custom Configuration

```python
# Custom confidence configuration
confidence_config = {
    "confidence_threshold": 0.8,  # Higher threshold
    "field_thresholds": {
        "date": 0.9,              # Very high threshold for dates
        "currency": 0.5,          # Lower threshold for currency
        "supplier": 0.8,          # High threshold for suppliers
        "line_item": 0.7          # Medium threshold for line items
    },
    "confidence_weights": {
        "ocr": 0.4,               # Higher weight for OCR confidence
        "normalization": 0.3,    # Lower weight for normalization
        "error": 0.2,            # Error penalty weight
        "context": 0.05,         # Context boost weight
        "cross_validation": 0.05  # Cross-validation weight
    }
}

normalizer = FieldNormalizer(confidence_config)
```

## Confidence Calculation

### Metrics

The system calculates confidence based on multiple factors:

1. **OCR Confidence**: From the OCR model output
2. **Normalization Confidence**: Based on successful parsing and validation
3. **Error Penalty**: Reduction for parsing errors and validation failures
4. **Context Boost**: Enhancement for known suppliers, region matching, etc.
5. **Cross-Validation Score**: Consistency checks across fields

### Formula

```
Overall Confidence = (OCR × 0.3) + (Normalization × 0.4) + (Context × 0.05) + (Cross-Validation × 0.05) - (Error Penalty × 0.2)
```

### Context Boosts

- **Known Suppliers**: +0.1 for suppliers in known list
- **Region Matching**: +0.05 for currency matching document region
- **Date Reasonableness**: +0.05 for dates within reasonable range
- **Mathematical Consistency**: +0.1 for price calculations that match

## Routing Decisions

### Auto-Accept Criteria

- Confidence score ≥ threshold
- No critical errors (parse errors, invalid formats)
- Successful normalization

### Needs-Review Criteria

- Confidence score < threshold
- Critical errors present
- Normalization failures
- Ambiguous data

### Error Handling

- Confidence calculation failures → ERROR routing
- Malformed data → ERROR routing
- System exceptions → ERROR routing with error details

## Review Candidates

### Structure

```python
@dataclass
class ReviewCandidate:
    field_name: str
    field_type: str
    raw_value: str
    normalized_value: Optional[Any]
    confidence_metrics: ConfidenceMetrics
    routing_result: RoutingResult
    error_details: List[str]
    suggestions: List[str]
    context: Dict[str, Any]
```

### Serialization

Review candidates can be serialized to JSON for UI display:

```python
candidate_dict = candidate.to_dict()
```

## Audit Logging

### Logged Information

- Field name and routing decision
- Confidence score and threshold used
- Error details and source artifacts
- Processing timestamps
- Overall result summaries

### Log Levels

- **INFO**: Routing decisions and summaries
- **WARNING**: Low confidence and errors
- **ERROR**: System failures and exceptions

## Testing

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: End-to-end pipeline testing
3. **Edge Case Tests**: Error handling and malformed data
4. **Performance Tests**: Large data structures and processing time

### Test Scenarios

- High-quality, clear invoice data
- Poor-quality, ambiguous invoice data
- OCR perturbations and handwriting overlays
- Mixed quality fields
- Empty and malformed data
- Extremely large data structures

## Configuration Options

### Global Settings

```python
{
    "confidence_threshold": 0.7,  # Default threshold
    "field_thresholds": {        # Field-specific thresholds
        "date": 0.8,
        "currency": 0.6,
        "supplier": 0.7,
        "line_item": 0.7
    },
    "confidence_weights": {      # Confidence calculation weights
        "ocr": 0.3,
        "normalization": 0.4,
        "error": 0.2,
        "context": 0.05,
        "cross_validation": 0.05
    }
}
```

### Field-Specific Thresholds

Different fields can have different confidence requirements:

- **Dates**: High threshold (0.8-0.9) due to format ambiguity
- **Currency**: Lower threshold (0.5-0.6) due to symbol recognition
- **Suppliers**: Medium threshold (0.7-0.8) for name matching
- **Line Items**: Medium threshold (0.7) for complex parsing

## Performance Considerations

### Processing Time

- Typical processing time: 0.1-0.5 seconds per invoice
- Large invoices (1000+ line items): 1-3 seconds
- Memory usage: ~10-50MB per invoice

### Optimization

- Confidence calculation is cached for repeated fields
- Batch processing for multiple invoices
- Asynchronous processing for large datasets

## Integration Points

### OCR Pipeline

The confidence routing system integrates seamlessly with the existing OCR pipeline:

1. **Input**: Raw OCR data from layout detection and table extraction
2. **Processing**: Field normalization with confidence calculation
3. **Output**: Normalized data with routing decisions and review candidates

### UI Integration

Review candidates are designed for easy UI integration:

```python
# Get review candidates for UI display
review_candidates = routing_result.review_candidates

for candidate in review_candidates:
    print(f"Field: {candidate.field_name}")
    print(f"Raw Value: {candidate.raw_value}")
    print(f"Confidence: {candidate.confidence_metrics.overall_confidence}")
    print(f"Errors: {candidate.error_details}")
```

### API Integration

The system provides JSON-serializable results for API endpoints:

```python
# Serialize results for API response
result_dict = {
    "overall_confidence": routing_result.overall_confidence,
    "auto_accepted_fields": routing_result.auto_accepted_fields,
    "review_candidates": [candidate.to_dict() for candidate in routing_result.review_candidates],
    "processing_time": routing_result.processing_time,
    "error_count": routing_result.error_count
}
```

## Error Handling

### Graceful Degradation

- Confidence calculation failures → Flag entire document for review
- Individual field failures → Route specific field for review
- System exceptions → Log errors and continue processing

### Error Types

1. **Parse Errors**: Invalid data formats
2. **Validation Errors**: Data range violations
3. **System Errors**: Calculation failures
4. **Configuration Errors**: Invalid settings

### Recovery Strategies

- Fallback to lower confidence thresholds
- Use default values for critical fields
- Route all fields for review in error cases

## Monitoring and Metrics

### Key Metrics

- Overall confidence distribution
- Auto-accept vs. review ratios
- Processing time per invoice
- Error rates by field type
- Review candidate resolution time

### Monitoring

- Log analysis for routing decisions
- Performance metrics for processing time
- Error tracking for system failures
- User feedback on review accuracy

## Future Enhancements

### Planned Features

1. **Machine Learning**: Learn from user corrections to improve confidence calculation
2. **Adaptive Thresholds**: Automatically adjust thresholds based on historical data
3. **Batch Processing**: Optimize for large-scale document processing
4. **Real-time Monitoring**: Dashboard for system performance and accuracy

### Integration Opportunities

1. **Workflow Automation**: Integrate with business process management
2. **Quality Assurance**: Automated testing and validation
3. **Analytics**: Business intelligence on document processing
4. **Compliance**: Audit trails for regulatory requirements

## Conclusion

The confidence routing and flagging system provides a robust foundation for automated invoice processing with human-in-the-loop quality control. It ensures high accuracy while minimizing manual review burden through intelligent routing decisions based on comprehensive confidence metrics.

The system is designed for scalability, maintainability, and integration with existing workflows, providing a solid foundation for production invoice processing systems.
