-- Add VAT summary zones column to supplier_templates table
ALTER TABLE supplier_templates ADD COLUMN vat_summary_zones_json TEXT; 