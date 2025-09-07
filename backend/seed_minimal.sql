PRAGMA foreign_keys=ON;

INSERT OR REPLACE INTO uploaded_files
(id, original_filename, canonical_path, file_size, file_hash, mime_type,
 doc_type, doc_type_confidence, upload_timestamp, processing_status, processing_progress,
 created_at, updated_at)
VALUES
('seed_file','seed.pdf','/tmp/seed.pdf',123,'deadbeef','application/pdf',
 'invoice',1.0,datetime('now'),'completed',100,datetime('now'),datetime('now'));

INSERT OR REPLACE INTO invoices
(id,file_id,total_amount_pennies,status,created_at,updated_at)
VALUES
('inv_seed','seed_file',7200,'parsed',datetime('now'),datetime('now'));

INSERT OR REPLACE INTO invoice_line_items
(id,invoice_id,row_idx,page,description,quantity,unit_price_pennies,line_total_pennies,created_at,updated_at)
VALUES
(4001,'inv_seed',0,1,'TIA MARIA 1L',6.0,1200,7200,datetime('now'),datetime('now'));
