#ifndef OWLIN_PREPROCESS_C_API_H
#define OWLIN_PREPROCESS_C_API_H

#ifdef __cplusplus
extern "C" {
#endif

// Error codes
#define OWLIN_PREPROCESS_SUCCESS 0
#define OWLIN_PREPROCESS_ERR_UNKNOWN 1
#define OWLIN_PREPROCESS_ERR_FILE_NOT_FOUND 2
#define OWLIN_PREPROCESS_ERR_MEMORY 3
#define OWLIN_PREPROCESS_ERR_INVALID_ARG 4
#define OWLIN_PREPROCESS_ERR_OPENCV 5
#define OWLIN_PREPROCESS_ERR_TESSERACT 6

/**
 * Preprocess an image file and return the result as a uchar* buffer.
 * Uses the original OpenCV-based preprocessing pipeline.
 *
 * @param filepath Path to the image file (JPEG, PNG, etc.)
 * @param width Output: image width (pixels)
 * @param height Output: image height (pixels)
 * @param channels Output: number of channels (should be 1 for binary image)
 * @return 0 on success, nonzero error code on failure. On success, buffer is allocated and must be freed by caller.
 *         On error, buffer is nullptr and error code is set.
 *         Logs steps and errors to stderr.
 */
int preprocess_image(const char* filepath, int* width, int* height, int* channels, unsigned char** out_buffer);

/**
 * Enhanced preprocessing using Tesseract algorithms when available.
 * Falls back to OpenCV algorithms if Tesseract is not available.
 * This is the recommended function for production use.
 *
 * @param filepath Path to the image file (JPEG, PNG, etc.)
 * @param width Output: image width (pixels)
 * @param height Output: image height (pixels)
 * @param channels Output: number of channels (should be 1 for binary image)
 * @return 0 on success, nonzero error code on failure. On success, buffer is allocated and must be freed by caller.
 *         On error, buffer is nullptr and error code is set.
 *         Logs steps and errors to stderr.
 */
int enhanced_preprocess_image(const char* filepath, int* width, int* height, int* channels, unsigned char** out_buffer);

/**
 * Enhanced preprocessing that takes an image buffer as input.
 * Useful for processing images already loaded in memory.
 *
 * @param input_buffer Input image buffer (row-major, uint8)
 * @param input_width Input image width
 * @param input_height Input image height
 * @param input_channels Input image channels (1 for grayscale, 3 for color)
 * @param width Output: processed image width (pixels)
 * @param height Output: processed image height (pixels)
 * @param channels Output: number of channels (should be 1 for binary image)
 * @param out_buffer Output: processed image buffer (allocated, must be freed by caller)
 * @return 0 on success, nonzero error code on failure
 */
int enhanced_preprocess_buffer(const unsigned char* input_buffer, int input_width, int input_height, int input_channels,
                              int* width, int* height, int* channels, unsigned char** out_buffer);

/**
 * Check if Tesseract preprocessing is available.
 * Returns 1 if available, 0 if not available.
 */
int is_tesseract_preprocessing_available();

/**
 * Get preprocessing timing information.
 * Returns a string describing the last preprocessing operation timing.
 * The returned string is static and should not be freed.
 */
const char* get_preprocessing_timing();

/**
 * Get a human-readable error string for the last error (thread-safe).
 */
const char* owlin_get_last_error();

#ifdef __cplusplus
}
#endif

#endif // OWLIN_PREPROCESS_C_API_H 