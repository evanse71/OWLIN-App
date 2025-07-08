#pragma once

#ifdef __cplusplus
extern "C" {
#endif

typedef struct OcrRecognizerImpl OcrRecognizer;

OcrRecognizer* ocr_create(const char* lang);
void ocr_destroy(OcrRecognizer* ocr);
int ocr_recognize(OcrRecognizer* ocr, const unsigned char* img, int width, int height, int channels, char** out_text, double* out_confidence);
/**
 * Batch recognize text from multiple images (lines/fields).
 * @param ocr Recognizer instance
 * @param imgs Array of pointers to image buffers (row-major, uint8)
 * @param widths Array of widths
 * @param heights Array of heights
 * @param channels Array of channels (should be 1)
 * @param n_images Number of images
 * @param out_texts Output: array of char* (allocated, must be freed with owlin_free)
 * @param out_confidences Output: array of double
 * @param out_errors Output: array of char* (allocated, must be freed)
 * @return 0 on success, nonzero on any error
 */
int ocr_recognize_batch(OcrRecognizer* ocr, const unsigned char** imgs, const int* widths, const int* heights, const int* channels, int n_images, char*** out_texts, double** out_confidences, char*** out_errors);
void owlin_free(void* ptr);
const char* owlin_get_last_error();

#ifdef __cplusplus
}
#endif 