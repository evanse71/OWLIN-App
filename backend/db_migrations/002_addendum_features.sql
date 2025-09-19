-- Migration 002: Addendum Features - Document Classification, Pairing, and Annotations
-- This migration adds the missing tables and fields for the addendum features

-- 1. DOC_PAIRS TABLE - Document pairing between invoices and delivery notes
CREATE TABLE IF NOT EXISTS doc_pairs (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    delivery_note_id TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0.0 AND score <= 1.0),
    pairing_method TEXT NOT NULL DEFAULT 'auto' CHECK (pairing_method IN ('auto', 'manual', 'fuzzy', 'exact')),
    supplier_match_score REAL DEFAULT 0.0,
    date_proximity_score REAL DEFAULT 0.0,
    line_item_similarity_score REAL DEFAULT 0.0,
    quantity_match_score REAL DEFAULT 0.0,
    price_match_score REAL DEFAULT 0.0,
    total_confidence REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'disputed', 'confirmed')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes(id) ON DELETE CASCADE,
    UNIQUE(invoice_id, delivery_note_id)
);

-- 2. ANNOTATIONS TABLE - User annotations on documents
CREATE TABLE IF NOT EXISTS annotations (
    id TEXT PRIMARY KEY,
    invoice_id TEXT,
    delivery_note_id TEXT,
    line_item_id INTEGER,
    kind TEXT NOT NULL CHECK (kind IN ('TICK', 'CROSS', 'CIRCLE', 'MARK', 'NOTE', 'HIGHLIGHT')),
    text TEXT, -- Extracted handwritten text (if any)
    x REAL NOT NULL CHECK (x >= 0.0 AND x <= 1.0), -- Normalized x coordinate
    y REAL NOT NULL CHECK (y >= 0.0 AND y <= 1.0), -- Normalized y coordinate
    w REAL NOT NULL CHECK (w >= 0.0 AND w <= 1.0), -- Normalized width
    h REAL NOT NULL CHECK (h >= 0.0 AND h <= 1.0), -- Normalized height
    confidence REAL NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    color TEXT, -- Detected color of annotation
    page_number INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes(id) ON DELETE CASCADE,
    FOREIGN KEY (line_item_id) REFERENCES invoice_line_items(id) ON DELETE CASCADE,
    CHECK ((invoice_id IS NOT NULL) OR (delivery_note_id IS NOT NULL))
);

-- 3. DOCUMENT_CLASSIFICATION TABLE - Document type classification results
CREATE TABLE IF NOT EXISTS document_classification (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK (doc_type IN ('invoice', 'delivery_note', 'receipt', 'credit_note', 'utility_bill', 'purchase_order', 'unknown')),
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    classification_method TEXT NOT NULL DEFAULT 'rule_based' CHECK (classification_method IN ('rule_based', 'ml_model', 'hybrid')),
    keywords_found TEXT, -- JSON array of keywords that led to classification
    layout_features TEXT, -- JSON object of layout-based features
    text_patterns TEXT, -- JSON array of text patterns matched
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
);

-- 4. PAIRING_RULES TABLE - Configurable pairing rules
CREATE TABLE IF NOT EXISTS pairing_rules (
    id TEXT PRIMARY KEY,
    rule_name TEXT NOT NULL UNIQUE,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('supplier_match', 'date_window', 'line_item_similarity', 'quantity_match', 'price_match')),
    parameters TEXT NOT NULL, -- JSON object with rule parameters
    weight REAL NOT NULL DEFAULT 1.0 CHECK (weight >= 0.0 AND weight <= 1.0),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 5. ANNOTATION_MAPPINGS TABLE - Maps annotations to specific line items
CREATE TABLE IF NOT EXISTS annotation_mappings (
    id TEXT PRIMARY KEY,
    annotation_id TEXT NOT NULL,
    line_item_id INTEGER NOT NULL,
    mapping_confidence REAL NOT NULL DEFAULT 0.0 CHECK (mapping_confidence >= 0.0 AND mapping_confidence <= 1.0),
    mapping_method TEXT NOT NULL DEFAULT 'proximity' CHECK (mapping_method IN ('proximity', 'manual', 'ml_model')),
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (annotation_id) REFERENCES annotations(id) ON DELETE CASCADE,
    FOREIGN KEY (line_item_id) REFERENCES invoice_line_items(id) ON DELETE CASCADE,
    UNIQUE(annotation_id, line_item_id)
);

-- Add doc_type and doc_type_confidence fields to existing tables if they don't exist
-- (These might already exist in the unified schema, but we'll add them safely)

-- Update uploaded_files table
ALTER TABLE uploaded_files ADD COLUMN doc_type_confidence REAL DEFAULT 0.0;

-- Update invoices table  
ALTER TABLE invoices ADD COLUMN doc_type_score REAL DEFAULT 1.0;

-- Update delivery_notes table
ALTER TABLE delivery_notes ADD COLUMN doc_type_score REAL DEFAULT 1.0;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_doc_pairs_invoice ON doc_pairs(invoice_id);
CREATE INDEX IF NOT EXISTS idx_doc_pairs_delivery_note ON doc_pairs(delivery_note_id);
CREATE INDEX IF NOT EXISTS idx_doc_pairs_score ON doc_pairs(score);
CREATE INDEX IF NOT EXISTS idx_doc_pairs_status ON doc_pairs(status);
CREATE INDEX IF NOT EXISTS idx_doc_pairs_method ON doc_pairs(pairing_method);

CREATE INDEX IF NOT EXISTS idx_annotations_invoice ON annotations(invoice_id);
CREATE INDEX IF NOT EXISTS idx_annotations_delivery_note ON annotations(delivery_note_id);
CREATE INDEX IF NOT EXISTS idx_annotations_line_item ON annotations(line_item_id);
CREATE INDEX IF NOT EXISTS idx_annotations_kind ON annotations(kind);
CREATE INDEX IF NOT EXISTS idx_annotations_page ON annotations(page_number);

CREATE INDEX IF NOT EXISTS idx_document_classification_file ON document_classification(file_id);
CREATE INDEX IF NOT EXISTS idx_document_classification_type ON document_classification(doc_type);
CREATE INDEX IF NOT EXISTS idx_document_classification_confidence ON document_classification(confidence);

CREATE INDEX IF NOT EXISTS idx_pairing_rules_type ON pairing_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_pairing_rules_enabled ON pairing_rules(enabled);

CREATE INDEX IF NOT EXISTS idx_annotation_mappings_annotation ON annotation_mappings(annotation_id);
CREATE INDEX IF NOT EXISTS idx_annotation_mappings_line_item ON annotation_mappings(line_item_id);

-- Create triggers for updated_at timestamps
CREATE TRIGGER IF NOT EXISTS update_doc_pairs_updated_at 
    AFTER UPDATE ON doc_pairs 
    BEGIN 
        UPDATE doc_pairs SET updated_at = datetime('now') WHERE id = NEW.id; 
    END;

CREATE TRIGGER IF NOT EXISTS update_annotations_updated_at 
    AFTER UPDATE ON annotations 
    BEGIN 
        UPDATE annotations SET updated_at = datetime('now') WHERE id = NEW.id; 
    END;

CREATE TRIGGER IF NOT EXISTS update_pairing_rules_updated_at 
    AFTER UPDATE ON pairing_rules 
    BEGIN 
        UPDATE pairing_rules SET updated_at = datetime('now') WHERE id = NEW.id; 
    END;

-- Insert default pairing rules
INSERT OR IGNORE INTO pairing_rules (id, rule_name, rule_type, parameters, weight, enabled) VALUES
('rule_001', 'Supplier Name Match', 'supplier_match', '{"threshold": 0.8, "fuzzy": true}', 0.4, 1),
('rule_002', 'Date Window Match', 'date_window', '{"window_days": 30, "strict": false}', 0.3, 1),
('rule_003', 'Line Item Similarity', 'line_item_similarity', '{"threshold": 0.7, "weight_description": 0.6, "weight_quantity": 0.4}', 0.2, 1),
('rule_004', 'Quantity Match', 'quantity_match', '{"tolerance": 0.1, "allow_partial": true}', 0.05, 1),
('rule_005', 'Price Match', 'price_match', '{"tolerance": 0.05, "allow_partial": true}', 0.05, 1);
