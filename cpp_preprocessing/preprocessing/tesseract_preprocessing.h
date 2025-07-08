#pragma once
#include <opencv2/opencv.hpp>
#include <string>
#include <memory>

// Forward declarations for Tesseract types
struct Pix;
struct Boxa;
struct Pta;

namespace owlin {
namespace preprocessing {

/**
 * Tesseract-based image processing algorithms
 * Provides enhanced preprocessing using Tesseract's native algorithms
 */
class TesseractPreprocessor {
public:
    TesseractPreprocessor();
    ~TesseractPreprocessor();
    
    // Disable copy constructor and assignment
    TesseractPreprocessor(const TesseractPreprocessor&) = delete;
    TesseractPreprocessor& operator=(const TesseractPreprocessor&) = delete;
    
    /**
     * Enhanced adaptive thresholding using Tesseract's algorithm
     * Combines Otsu thresholding with local adaptive thresholding
     */
    cv::Mat tesseract_adaptive_threshold(const cv::Mat& img);
    
    /**
     * Tesseract's projection-based deskewing algorithm
     * More robust than OpenCV's minAreaRect for text images
     */
    cv::Mat tesseract_deskew(const cv::Mat& img);
    
    /**
     * Tesseract's quadrangle detection and dewarping
     * Uses Tesseract's page segmentation for better results
     */
    cv::Mat tesseract_dewarp(const cv::Mat& img);
    
    /**
     * Tesseract's noise reduction using morphological operations
     * Optimized for document images
     */
    cv::Mat tesseract_denoise(const cv::Mat& img);
    
    /**
     * Tesseract's contrast enhancement
     * Histogram equalization with document-specific parameters
     */
    cv::Mat tesseract_enhance_contrast(const cv::Mat& img);
    
    /**
     * Tesseract's automatic border removal
     * Detects and removes page borders automatically
     */
    cv::Mat tesseract_remove_borders(const cv::Mat& img);
    
    /**
     * Full Tesseract preprocessing pipeline
     * Combines all Tesseract algorithms in optimal order
     */
    cv::Mat tesseract_preprocess_pipeline(const cv::Mat& img);
    
    /**
     * Check if Tesseract preprocessing is available
     */
    bool is_available() const;

private:
    // Tesseract image data
    struct Pix* pix_;
    
    // Helper functions
    cv::Mat pix_to_mat(struct Pix* pix);
    struct Pix* mat_to_pix(const cv::Mat& mat);
    void cleanup_pix();
    
    // Tesseract algorithm implementations
    cv::Mat apply_tesseract_thresholding(struct Pix* pix);
    cv::Mat apply_tesseract_deskewing(struct Pix* pix);
    cv::Mat apply_tesseract_dewarping(struct Pix* pix);
    cv::Mat apply_tesseract_denoising(struct Pix* pix);
    cv::Mat apply_tesseract_contrast_enhancement(struct Pix* pix);
    cv::Mat apply_tesseract_border_removal(struct Pix* pix);
};

/**
 * Hybrid preprocessing that combines OpenCV and Tesseract algorithms
 * Falls back to OpenCV if Tesseract is not available
 */
class HybridPreprocessor {
public:
    HybridPreprocessor();
    ~HybridPreprocessor() = default;
    
    /**
     * Smart adaptive thresholding - uses Tesseract if available, OpenCV otherwise
     */
    cv::Mat smart_adaptive_threshold(const cv::Mat& img);
    
    /**
     * Smart deskewing - uses Tesseract if available, OpenCV otherwise
     */
    cv::Mat smart_deskew(const cv::Mat& img);
    
    /**
     * Smart dewarping - uses Tesseract if available, OpenCV otherwise
     */
    cv::Mat smart_dewarp(const cv::Mat& img);
    
    /**
     * Smart denoising - uses Tesseract if available, OpenCV otherwise
     */
    cv::Mat smart_denoise(const cv::Mat& img);
    
    /**
     * Enhanced preprocessing pipeline with fallback logic
     */
    cv::Mat enhanced_preprocess_pipeline(const cv::Mat& img);

private:
    std::unique_ptr<TesseractPreprocessor> tess_preprocessor_;
    bool tesseract_available_;
};

} // namespace preprocessing
} // namespace owlin 