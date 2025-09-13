#pragma once
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Error codes
#define OWLIN_OCR_SUCCESS 0
#define OWLIN_OCR_ERR_UNKNOWN 1
#define OWLIN_OCR_ERR_FILE_NOT_FOUND 2
#define OWLIN_OCR_ERR_PREPROCESS 3
#define OWLIN_OCR_ERR_OCR 4

/**
 * Run the full OCR pipeline on an image file.
 * @param filepath Path to the image file
 * @param out_text_ptr Pointer to char* (allocated, must be freed by caller)
 * @param out_confidence Pointer to double (confidence score)
 * @return 0 on success, nonzero error code on failure
 */
int owlin_ocr_from_file(const char* filepath, char** out_text_ptr, double* out_confidence);

/**
 * Run the full OCR pipeline on a raw image buffer (uchar*, row-major, grayscale).
 * @param buffer Image data
 * @param width Image width
 * @param height Image height
 * @param channels Number of channels (should be 1)
 * @param out_text_ptr Pointer to char* (allocated, must be freed by caller)
 * @param out_confidence Pointer to double (confidence score)
 * @return 0 on success, nonzero error code on failure
 */
int owlin_ocr_from_buffer(const unsigned char* buffer, int width, int height, int channels, char** out_text_ptr, double* out_confidence);

/**
 * Free memory allocated by the API (for text buffers).
 */
void owlin_ocr_free(void* ptr);

/**
 * Get a human-readable error message for an error code.
 */
const char* owlin_ocr_strerror(int errcode);

#ifdef __cplusplus
}
#endif

/*
Python ctypes usage example:

import ctypes
lib = ctypes.CDLL("./libowlin_ocr.so")
lib.owlin_ocr_from_file.restype = ctypes.c_int
lib.owlin_ocr_from_file.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_double)]
lib.owlin_ocr_free.restype = None
lib.owlin_ocr_free.argtypes = [ctypes.c_void_p]

text_ptr = ctypes.c_char_p()
conf = ctypes.c_double()
err = lib.owlin_ocr_from_file(b"invoice.jpg", ctypes.byref(text_ptr), ctypes.byref(conf))
if err == 0:
    print("OCR text:", text_ptr.value.decode())
    print("Confidence:", conf.value)
    lib.owlin_ocr_free(text_ptr)
else:
    print("Error:", lib.owlin_ocr_strerror(err))
*/ 