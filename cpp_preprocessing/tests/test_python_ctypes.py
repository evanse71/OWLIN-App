import ctypes
import os
import sys
import pytest
import numpy as np
import cv2

# Assume shared libraries are built and available in ../lib or ..
libpath = os.path.join(os.path.dirname(__file__), "..", "libowlin_recognition.so")
lib = ctypes.CDLL(libpath)

lib.ocr_create.restype = ctypes.c_void_p
lib.ocr_create.argtypes = [ctypes.c_char_p]
lib.ocr_destroy.restype = None
lib.ocr_destroy.argtypes = [ctypes.c_void_p]
lib.ocr_recognize.restype = ctypes.c_int
lib.ocr_recognize.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_double)
]
lib.owlin_free.restype = None
lib.owlin_free.argtypes = [ctypes.c_void_p]
lib.owlin_get_last_error.restype = ctypes.c_char_p

@pytest.fixture
def sample_image():
    img = cv2.imread(os.path.join(os.path.dirname(__file__), "mock_invoice_line.png"), cv2.IMREAD_GRAYSCALE)
    assert img is not None and img.size > 0
    return img

def test_recognition_valid(sample_image):
    h, w = sample_image.shape
    img_ptr = sample_image.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
    ocr = lib.ocr_create(b"eng")
    assert ocr
    out_text = ctypes.c_char_p()
    conf = ctypes.c_double()
    err = lib.ocr_recognize(ocr, img_ptr, w, h, 1, ctypes.byref(out_text), ctypes.byref(conf))
    assert err == 0
    assert out_text.value is not None and len(out_text.value.decode()) > 0
    assert conf.value > 0.0
    lib.owlin_free(out_text)
    lib.ocr_destroy(ocr)

def test_recognition_invalid():
    ocr = lib.ocr_create(b"eng")
    assert ocr
    out_text = ctypes.c_char_p()
    conf = ctypes.c_double()
    err = lib.ocr_recognize(ocr, None, 0, 0, 1, ctypes.byref(out_text), ctypes.byref(conf))
    assert err != 0
    assert lib.owlin_get_last_error().decode() != ""
    lib.ocr_destroy(ocr) 