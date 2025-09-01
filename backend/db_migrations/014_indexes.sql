-- 014_indexes.sql
-- Add critical indexes for performance

-- Invoice line items lookup (prevents API slowdown)
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id
ON invoice_line_items(invoice_id);

-- Invoice creation date (for sorting/filtering)
CREATE INDEX IF NOT EXISTS idx_invoices_created_at 
ON invoices(created_at);

-- Invoice pages lookup
CREATE INDEX IF NOT EXISTS idx_pages_invoice 
ON invoice_pages(invoice_id);

-- Delivery line items lookup
CREATE INDEX IF NOT EXISTS idx_delivery_items_dn_id
ON delivery_line_items(delivery_note_id);

-- Match links lookup
CREATE INDEX IF NOT EXISTS idx_match_links_invoice
ON match_links(invoice_id);

-- Match link items lookup  
CREATE INDEX IF NOT EXISTS idx_match_items_link
ON match_link_items(link_id); 