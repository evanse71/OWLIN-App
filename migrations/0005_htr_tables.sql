-- Migration 0005: Add HTR (Handwriting Recognition) tables
-- This migration adds tables for storing HTR training samples, models, and predictions

-- HTR samples table for training data
CREATE TABLE IF NOT EXISTS htr_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id TEXT UNIQUE NOT NULL,
    image_path TEXT NOT NULL,
    ground_truth TEXT NOT NULL,
    confidence REAL NOT NULL,
    model_used TEXT NOT NULL,
    metadata TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

-- HTR models table for model management
CREATE TABLE IF NOT EXISTS htr_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT UNIQUE NOT NULL,
    model_path TEXT NOT NULL,
    model_type TEXT NOT NULL,
    version TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

-- HTR predictions table for storing prediction results
CREATE TABLE IF NOT EXISTS htr_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    page_num INTEGER NOT NULL,
    block_id TEXT NOT NULL,
    text TEXT NOT NULL,
    confidence REAL NOT NULL,
    model_used TEXT NOT NULL,
    bbox TEXT NOT NULL,
    processing_time REAL NOT NULL,
    created_at REAL NOT NULL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_htr_samples_model ON htr_samples(model_used);
CREATE INDEX IF NOT EXISTS idx_htr_samples_confidence ON htr_samples(confidence);
CREATE INDEX IF NOT EXISTS idx_htr_samples_created ON htr_samples(created_at);
CREATE INDEX IF NOT EXISTS idx_htr_predictions_doc ON htr_predictions(document_id);
CREATE INDEX IF NOT EXISTS idx_htr_predictions_page ON htr_predictions(page_num);
CREATE INDEX IF NOT EXISTS idx_htr_predictions_created ON htr_predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_htr_models_type ON htr_models(model_type);
