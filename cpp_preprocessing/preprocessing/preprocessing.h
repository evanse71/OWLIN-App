#pragma once
#include <opencv2/opencv.hpp>
#include <string>

namespace owlin {
namespace preprocessing {

/**
 * Load an image from file path (color).
 * Throws std::runtime_error on failure.
 */
cv::Mat load_image(const std::string& path);

/**
 * Convert a BGR image to grayscale.
 */
cv::Mat to_grayscale(const cv::Mat& img);

/**
 * Resize an image by a scale factor (default 1.5) using bicubic interpolation.
 */
cv::Mat resize_image(const cv::Mat& img, double scale = 1.5);

/**
 * Apply adaptive Gaussian thresholding (block size 31, C=10).
 */
cv::Mat adaptive_gaussian_threshold(const cv::Mat& img);

/**
 * Deskew a binary image using minAreaRect on non-zero pixels.
 */
cv::Mat deskew(const cv::Mat& bin_img);

/**
 * Dewarp an image to correct perspective distortions (for invoices).
 */
cv::Mat dewarp(const cv::Mat& img);

/**
 * Remove background to isolate text from noisy or colored backgrounds.
 */
cv::Mat remove_background(const cv::Mat& img);

/**
 * Detect and correct image orientation (portrait/landscape, upside-down).
 * Returns a rotated image in correct orientation.
 */
cv::Mat auto_orient(const cv::Mat& img);

/**
 * Improved denoising filter tuned for invoice scans/photos.
 */
cv::Mat invoice_denoise(const cv::Mat& img);

/**
 * Run the full preprocessing pipeline: load, grayscale, resize, threshold, deskew.
 * Prints image info after each step.
 */
cv::Mat preprocess_pipeline(const std::string& path);

// --- NEW: Enhanced Preprocessing with Tesseract Integration ---

/**
 * Enhanced preprocessing pipeline that uses Tesseract algorithms when available.
 * Falls back to OpenCV algorithms if Tesseract is not available.
 * This is the recommended pipeline for production use.
 */
cv::Mat enhanced_preprocess_pipeline(const std::string& path);

/**
 * Enhanced preprocessing pipeline that takes a loaded image.
 * Uses hybrid approach: Tesseract algorithms with OpenCV fallback.
 */
cv::Mat enhanced_preprocess_image(const cv::Mat& img);

/**
 * Get the last timing information from Tesseract preprocessing.
 * Returns timing string or empty string if no timing available.
 */
std::string get_tesseract_timing();

/**
 * Check if Tesseract preprocessing is available.
 * Returns true if Tesseract/Leptonica libraries are available.
 */
bool is_tesseract_preprocessing_available();

} // namespace preprocessing
} // namespace owlin 