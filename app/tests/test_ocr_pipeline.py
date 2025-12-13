import pytest
import numpy as np
import cv2
from app.ocr_factory import get_ocr_recognizer
import streamlit as st

def sample_invoice_image():
    # Replace with a real test image path or generate a dummy image
    img = cv2.imread("../tests/mock_invoice.png")
    if img is None:
        # Create a dummy white image for fallback
        img = np.ones((100, 300), dtype=np.uint8) * 255
    return img

def test_tesseract_ocr(monkeypatch):
    monkeypatch.setitem(st.session_state, 'ocr_engine', 'Tesseract (default)')
    recognizer = get_ocr_recognizer()
    img = sample_invoice_image()
    text, conf = recognizer.recognize(img)
    print(f"Tesseract output: {text}\nConfidence: {conf}")
    assert isinstance(text, str)
    assert isinstance(conf, float)
    assert conf >= 0.0

def test_easyocr_ocr(monkeypatch):
    monkeypatch.setitem(st.session_state, 'ocr_engine', 'EasyOCR')
    recognizer = get_ocr_recognizer()
    img = sample_invoice_image()
    text, conf = recognizer.recognize(img)
    print(f"EasyOCR output: {text}\nConfidence: {conf}")
    assert isinstance(text, str)
    assert isinstance(conf, float)
    assert conf >= 0.0

def test_engine_switching(monkeypatch):
    monkeypatch.setitem(st.session_state, 'ocr_engine', 'Tesseract (default)')
    rec1 = get_ocr_recognizer()
    monkeypatch.setitem(st.session_state, 'ocr_engine', 'EasyOCR')
    rec2 = get_ocr_recognizer()
    assert rec1.__class__.__name__ != rec2.__class__.__name__

# Integration test: both engines on the same image
def test_ocr_pipeline_integration(monkeypatch):
    img = sample_invoice_image()
    for engine in ['Tesseract (default)', 'EasyOCR']:
        monkeypatch.setitem(st.session_state, 'ocr_engine', engine)
        recognizer = get_ocr_recognizer()
        text, conf = recognizer.recognize(img)
        print(f"Engine: {engine}, Output: {text}, Confidence: {conf}")
        assert isinstance(text, str)
        assert isinstance(conf, float) 