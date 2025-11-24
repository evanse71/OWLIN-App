# Supplier Template Library

This directory contains YAML templates for supplier-specific invoice processing overrides. Templates help improve accuracy by providing supplier-specific patterns for field extraction and validation.

## Template Structure

Each template is a YAML file with the following structure:

```yaml
name: "Supplier Name"
version: "1.0"
description: "Template description"

supplier:
  name: "Primary Supplier Name"
  aliases: ["Alternative Name 1", "Alternative Name 2"]
  vat_ids: ["GB123456789"]
  header_tokens: ["Key", "Tokens", "In", "Header"]

field_overrides:
  total:
    patterns: ["Total.*?£([0-9,]+\.?[0-9]*)", "Amount.*?£([0-9,]+\.?[0-9]*)"]
    currency_symbols: ["£", "GBP"]
  vat_total:
    patterns: ["VAT.*?£([0-9,]+\.?[0-9]*)", "Tax.*?£([0-9,]+\.?[0-9]*)"]
    currency_symbols: ["£", "GBP"]
  date:
    patterns: ["Date.*?([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", "Invoice Date.*?([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})"]
    format: "DD/MM/YYYY"

processing:
  fuzzy_threshold: 0.8
  case_sensitive: false
  priority: 10
```

## Adding a New Template

1. **Create a new YAML file** in this directory with the supplier name (e.g., `supplier_name.yaml`)

2. **Fill in the basic information**:
   - `name`: Human-readable template name
   - `version`: Template version (start with "1.0")
   - `description`: Brief description of the supplier

3. **Define supplier identification**:
   - `supplier.name`: Primary supplier name
   - `supplier.aliases`: Alternative names or variations
   - `supplier.vat_ids`: VAT registration numbers (if known)
   - `supplier.header_tokens`: Key words that appear in invoice headers

4. **Add field override patterns**:
   - `total.patterns`: Regex patterns to extract total amount
   - `vat_total.patterns`: Regex patterns to extract VAT amount
   - `date.patterns`: Regex patterns to extract invoice date
   - `currency_symbols`: Currency symbols used by this supplier

5. **Set processing rules**:
   - `fuzzy_threshold`: Matching threshold (0.0-1.0, higher = more strict)
   - `case_sensitive`: Whether matching is case-sensitive
   - `priority`: Template priority (higher numbers = more important)

## Template Matching

Templates are matched using fuzzy string matching on:
- Supplier name (from invoice)
- Header text tokens
- VAT IDs (if available)

The system will:
1. Try exact matches first
2. Fall back to fuzzy matching if no exact match
3. Use the highest priority template if multiple matches

## Field Overrides

Templates only override **missing** fields. They will never replace existing non-empty values.

Supported override fields:
- `total`: Invoice total amount
- `vat_total`: VAT/tax amount
- `date`: Invoice date
- `line_items`: Line item processing rules

## Regex Pattern Examples

### Total Amount Patterns
```yaml
total:
  patterns: 
    - "Total.*?£([0-9,]+\.?[0-9]*)"
    - "Amount.*?£([0-9,]+\.?[0-9]*)"
    - "Net Total.*?([0-9,]+\.?[0-9]*)"
  currency_symbols: ["£", "GBP"]
```

### Date Patterns
```yaml
date:
  patterns:
    - "Date.*?([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})"
    - "Invoice Date.*?([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})"
    - "Due Date.*?([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})"
  format: "DD/MM/YYYY"
```

### VAT Patterns
```yaml
vat_total:
  patterns:
    - "VAT.*?£([0-9,]+\.?[0-9]*)"
    - "Tax.*?£([0-9,]+\.?[0-9]*)"
    - "VAT @ 20%.*?£([0-9,]+\.?[0-9]*)"
  currency_symbols: ["£", "GBP"]
```

## Testing Templates

After creating a template, test it by:

1. **Running the test suite**: `python -m pytest tests/test_template_system.py`
2. **Manual testing**: Use the template matcher directly
3. **Integration testing**: Process a real invoice with the template

## Best Practices

1. **Use specific patterns**: More specific regex patterns are better than generic ones
2. **Test thoroughly**: Test patterns with real invoice data
3. **Keep it simple**: Avoid overly complex regex patterns
4. **Document patterns**: Add comments explaining complex patterns
5. **Version control**: Increment version when making changes

## Troubleshooting

### Template Not Matching
- Check supplier name variations in `aliases`
- Verify `header_tokens` are present in invoice headers
- Lower the `fuzzy_threshold` if needed

### Overrides Not Working
- Verify regex patterns are correct
- Check that patterns match the actual invoice format
- Ensure currency symbols are correct

### YAML Parse Errors
- Validate YAML syntax with an online validator
- Check indentation (use spaces, not tabs)
- Ensure all required fields are present

## File Naming Convention

Use lowercase with underscores: `supplier_name.yaml`

Examples:
- `brakes.yaml`
- `bidfood.yaml`
- `molson_coors.yaml`
- `metro_supplies.yaml`
