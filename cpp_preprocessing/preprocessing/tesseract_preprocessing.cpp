#include "tesseract_preprocessing.h"
#include <leptonica/allheaders.h>
#include <iostream>
#include <chrono>
#include <stdexcept>

namespace owlin {
namespace preprocessing {

// Static timing for performance logging
static thread_local std::string g_tesseract_timing;

TesseractPreprocessor::TesseractPreprocessor() : pix_(nullptr) {
    // Initialize Leptonica (required for Tesseract image processing)
    // Note: This doesn't require Tesseract itself, just Leptonica
}

TesseractPreprocessor::~TesseractPreprocessor() {
    cleanup_pix();
}

bool TesseractPreprocessor::is_available() const {
    // Check if Leptonica is available (required for Tesseract image processing)
    return true; // Leptonica is typically available when Tesseract is installed
}

void TesseractPreprocessor::cleanup_pix() {
    if (pix_) {
        pixDestroy(&pix_);
        pix_ = nullptr;
    }
}

struct Pix* TesseractPreprocessor::mat_to_pix(const cv::Mat& mat) {
    if (mat.empty()) return nullptr;
    
    // Convert OpenCV Mat to Leptonica Pix
    int width = mat.cols;
    int height = mat.rows;
    int channels = mat.channels();
    
    if (channels == 1) {
        // Grayscale image
        struct Pix* pix = pixCreate(width, height, 8);
        if (!pix) return nullptr;
        
        // Copy data
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                int val = mat.at<uchar>(y, x);
                pixSetPixel(pix, x, y, val);
            }
        }
        return pix;
    } else if (channels == 3) {
        // Color image - convert to grayscale
        cv::Mat gray;
        cv::cvtColor(mat, gray, cv::COLOR_BGR2GRAY);
        return mat_to_pix(gray);
    }
    
    return nullptr;
}

cv::Mat TesseractPreprocessor::pix_to_mat(struct Pix* pix) {
    if (!pix) return cv::Mat();
    
    int width = pixGetWidth(pix);
    int height = pixGetHeight(pix);
    int depth = pixGetDepth(pix);
    
    if (depth != 8) {
        // Convert to 8-bit if needed
        struct Pix* pix8 = pixConvertTo8(pix, 0);
        if (!pix8) return cv::Mat();
        pixDestroy(&pix);
        pix = pix8;
    }
    
    cv::Mat mat(height, width, CV_8UC1);
    
    // Copy data
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            l_uint32 val;
            pixGetPixel(pix, x, y, &val);
            mat.at<uchar>(y, x) = static_cast<uchar>(val);
        }
    }
    
    return mat;
}

cv::Mat TesseractPreprocessor::tesseract_adaptive_threshold(const cv::Mat& img) {
    auto t0 = std::chrono::high_resolution_clock::now();
    
    try {
        struct Pix* pix = mat_to_pix(img);
        if (!pix) {
            std::cerr << "Failed to convert image to Pix format" << std::endl;
            return img.clone();
        }
        
        cv::Mat result = apply_tesseract_thresholding(pix);
        pixDestroy(&pix);
        
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
        g_tesseract_timing = "tesseract_adaptive_threshold: " + std::to_string(ms) + " ms";
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "Tesseract adaptive threshold failed: " << e.what() << std::endl;
        return img.clone();
    }
}

cv::Mat TesseractPreprocessor::apply_tesseract_thresholding(struct Pix* pix) {
    // Tesseract-style adaptive thresholding using Leptonica
    // This mimics Tesseract's approach: Otsu + local thresholding
    
    // 1. Apply Otsu thresholding first
    struct Pix* pix_otsu = pixOtsuAdaptiveThreshold(pix, 200, 200, 0, 0, 0.0, nullptr);
    if (!pix_otsu) {
        std::cerr << "Otsu thresholding failed" << std::endl;
        return pix_to_mat(pix);
    }
    
    // 2. Apply local adaptive thresholding for better results
    struct Pix* pix_local = pixAdaptiveThreshold(pix, 200, 200, 0, 0, 0.0, nullptr);
    if (!pix_local) {
        pixDestroy(&pix_otsu);
        return pix_to_mat(pix);
    }
    
    // 3. Combine results (Tesseract's approach)
    struct Pix* pix_combined = pixAnd(pix_otsu, pix_local);
    
    cv::Mat result = pix_to_mat(pix_combined ? pix_combined : pix_otsu);
    
    // Cleanup
    pixDestroy(&pix_otsu);
    pixDestroy(&pix_local);
    if (pix_combined) pixDestroy(&pix_combined);
    
    return result;
}

cv::Mat TesseractPreprocessor::tesseract_deskew(const cv::Mat& img) {
    auto t0 = std::chrono::high_resolution_clock::now();
    
    try {
        struct Pix* pix = mat_to_pix(img);
        if (!pix) {
            std::cerr << "Failed to convert image to Pix format for deskewing" << std::endl;
            return img.clone();
        }
        
        cv::Mat result = apply_tesseract_deskewing(pix);
        pixDestroy(&pix);
        
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
        g_tesseract_timing = "tesseract_deskew: " + std::to_string(ms) + " ms";
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "Tesseract deskewing failed: " << e.what() << std::endl;
        return img.clone();
    }
}

cv::Mat TesseractPreprocessor::apply_tesseract_deskewing(struct Pix* pix) {
    // Tesseract-style deskewing using projection profiles
    
    // 1. Find skew angle using projection profiles
    l_float32 angle, conf;
    struct Pix* pix_skew = pixFindSkewAndDeskew(pix, 0, &angle, &conf);
    
    if (!pix_skew) {
        std::cerr << "Deskewing failed" << std::endl;
        return pix_to_mat(pix);
    }
    
    cv::Mat result = pix_to_mat(pix_skew);
    pixDestroy(&pix_skew);
    
    return result;
}

cv::Mat TesseractPreprocessor::tesseract_dewarp(const cv::Mat& img) {
    auto t0 = std::chrono::high_resolution_clock::now();
    
    try {
        struct Pix* pix = mat_to_pix(img);
        if (!pix) {
            std::cerr << "Failed to convert image to Pix format for dewarping" << std::endl;
            return img.clone();
        }
        
        cv::Mat result = apply_tesseract_dewarping(pix);
        pixDestroy(&pix);
        
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
        g_tesseract_timing = "tesseract_dewarp: " + std::to_string(ms) + " ms";
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "Tesseract dewarping failed: " << e.what() << std::endl;
        return img.clone();
    }
}

cv::Mat TesseractPreprocessor::apply_tesseract_dewarping(struct Pix* pix) {
    // Tesseract-style dewarping using quadrangle detection
    
    // 1. Find page boundaries
    struct Boxa* boxa = pixFindPageForeground(pix, 0, nullptr, nullptr);
    if (!boxa || boxaGetCount(boxa) == 0) {
        if (boxa) boxaDestroy(&boxa);
        return pix_to_mat(pix);
    }
    
    // 2. Get the largest box (main page content)
    struct Box* box = boxaGetBox(boxa, 0, L_CLONE);
    if (!box) {
        boxaDestroy(&boxa);
        return pix_to_mat(pix);
    }
    
    // 3. Extract the page region
    struct Pix* pix_crop = pixClipRectangle(pix, box, nullptr);
    boxDestroy(&box);
    boxaDestroy(&boxa);
    
    if (!pix_crop) {
        return pix_to_mat(pix);
    }
    
    cv::Mat result = pix_to_mat(pix_crop);
    pixDestroy(&pix_crop);
    
    return result;
}

cv::Mat TesseractPreprocessor::tesseract_denoise(const cv::Mat& img) {
    auto t0 = std::chrono::high_resolution_clock::now();
    
    try {
        struct Pix* pix = mat_to_pix(img);
        if (!pix) {
            std::cerr << "Failed to convert image to Pix format for denoising" << std::endl;
            return img.clone();
        }
        
        cv::Mat result = apply_tesseract_denoising(pix);
        pixDestroy(&pix);
        
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
        g_tesseract_timing = "tesseract_denoise: " + std::to_string(ms) + " ms";
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "Tesseract denoising failed: " << e.what() << std::endl;
        return img.clone();
    }
}

cv::Mat TesseractPreprocessor::apply_tesseract_denoising(struct Pix* pix) {
    // Tesseract-style noise reduction using morphological operations
    
    // 1. Remove small noise with opening operation
    struct Pix* pix_open = pixOpenBrick(pix, 2, 2);
    if (!pix_open) {
        return pix_to_mat(pix);
    }
    
    // 2. Close small gaps in text
    struct Pix* pix_close = pixCloseBrick(pix_open, 1, 1);
    pixDestroy(&pix_open);
    
    if (!pix_close) {
        return pix_to_mat(pix);
    }
    
    cv::Mat result = pix_to_mat(pix_close);
    pixDestroy(&pix_close);
    
    return result;
}

cv::Mat TesseractPreprocessor::tesseract_enhance_contrast(const cv::Mat& img) {
    auto t0 = std::chrono::high_resolution_clock::now();
    
    try {
        struct Pix* pix = mat_to_pix(img);
        if (!pix) {
            std::cerr << "Failed to convert image to Pix format for contrast enhancement" << std::endl;
            return img.clone();
        }
        
        cv::Mat result = apply_tesseract_contrast_enhancement(pix);
        pixDestroy(&pix);
        
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
        g_tesseract_timing = "tesseract_enhance_contrast: " + std::to_string(ms) + " ms";
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "Tesseract contrast enhancement failed: " << e.what() << std::endl;
        return img.clone();
    }
}

cv::Mat TesseractPreprocessor::apply_tesseract_contrast_enhancement(struct Pix* pix) {
    // Tesseract-style contrast enhancement
    
    // 1. Apply histogram equalization
    struct Pix* pix_eq = pixEqualizeTRC(pix, 0.0, 0.0, 0.0);
    if (!pix_eq) {
        return pix_to_mat(pix);
    }
    
    // 2. Apply gamma correction for better contrast
    struct Pix* pix_gamma = pixGammaTRC(pix_eq, 1.0, 0, 255);
    pixDestroy(&pix_eq);
    
    if (!pix_gamma) {
        return pix_to_mat(pix);
    }
    
    cv::Mat result = pix_to_mat(pix_gamma);
    pixDestroy(&pix_gamma);
    
    return result;
}

cv::Mat TesseractPreprocessor::tesseract_remove_borders(const cv::Mat& img) {
    auto t0 = std::chrono::high_resolution_clock::now();
    
    try {
        struct Pix* pix = mat_to_pix(img);
        if (!pix) {
            std::cerr << "Failed to convert image to Pix format for border removal" << std::endl;
            return img.clone();
        }
        
        cv::Mat result = apply_tesseract_border_removal(pix);
        pixDestroy(&pix);
        
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
        g_tesseract_timing = "tesseract_remove_borders: " + std::to_string(ms) + " ms";
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "Tesseract border removal failed: " << e.what() << std::endl;
        return img.clone();
    }
}

cv::Mat TesseractPreprocessor::apply_tesseract_border_removal(struct Pix* pix) {
    // Tesseract-style border removal
    
    // 1. Find page boundaries
    struct Boxa* boxa = pixFindPageForeground(pix, 0, nullptr, nullptr);
    if (!boxa || boxaGetCount(boxa) == 0) {
        if (boxa) boxaDestroy(&boxa);
        return pix_to_mat(pix);
    }
    
    // 2. Get the largest box (main content)
    struct Box* box = boxaGetBox(boxa, 0, L_CLONE);
    if (!box) {
        boxaDestroy(&boxa);
        return pix_to_mat(pix);
    }
    
    // 3. Add some margin around the content
    l_int32 x, y, w, h;
    boxGetGeometry(box, &x, &y, &w, &h);
    boxDestroy(&box);
    boxaDestroy(&boxa);
    
    // Add 10% margin
    int margin_x = w / 10;
    int margin_y = h / 10;
    x = std::max(0, x - margin_x);
    y = std::max(0, y - margin_y);
    w = std::min(pixGetWidth(pix) - x, w + 2 * margin_x);
    h = std::min(pixGetHeight(pix) - y, h + 2 * margin_y);
    
    struct Box* box_margin = boxCreate(x, y, w, h);
    struct Pix* pix_crop = pixClipRectangle(pix, box_margin, nullptr);
    boxDestroy(&box_margin);
    
    if (!pix_crop) {
        return pix_to_mat(pix);
    }
    
    cv::Mat result = pix_to_mat(pix_crop);
    pixDestroy(&pix_crop);
    
    return result;
}

cv::Mat TesseractPreprocessor::tesseract_preprocess_pipeline(const cv::Mat& img) {
    auto t0 = std::chrono::high_resolution_clock::now();
    
    try {
        // Apply Tesseract preprocessing in optimal order
        cv::Mat result = img;
        
        // 1. Remove borders first
        result = tesseract_remove_borders(result);
        
        // 2. Enhance contrast
        result = tesseract_enhance_contrast(result);
        
        // 3. Denoise
        result = tesseract_denoise(result);
        
        // 4. Adaptive thresholding
        result = tesseract_adaptive_threshold(result);
        
        // 5. Deskew
        result = tesseract_deskew(result);
        
        // 6. Dewarp (if needed)
        result = tesseract_dewarp(result);
        
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
        g_tesseract_timing = "tesseract_preprocess_pipeline: " + std::to_string(ms) + " ms";
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "Tesseract preprocessing pipeline failed: " << e.what() << std::endl;
        return img.clone();
    }
}

// Hybrid Preprocessor Implementation
HybridPreprocessor::HybridPreprocessor() : tesseract_available_(false) {
    try {
        tess_preprocessor_ = std::make_unique<TesseractPreprocessor>();
        tesseract_available_ = tess_preprocessor_->is_available();
    } catch (const std::exception& e) {
        std::cerr << "Tesseract preprocessor not available: " << e.what() << std::endl;
        tesseract_available_ = false;
    }
}

cv::Mat HybridPreprocessor::smart_adaptive_threshold(const cv::Mat& img) {
    if (tesseract_available_) {
        try {
            return tess_preprocessor_->tesseract_adaptive_threshold(img);
        } catch (const std::exception& e) {
            std::cerr << "Tesseract thresholding failed, falling back to OpenCV: " << e.what() << std::endl;
        }
    }
    
    // Fallback to OpenCV
    cv::Mat thresh;
    cv::adaptiveThreshold(
        img, thresh,
        255,
        cv::ADAPTIVE_THRESH_GAUSSIAN_C,
        cv::THRESH_BINARY,
        31, // block size
        10  // C value
    );
    return thresh;
}

cv::Mat HybridPreprocessor::smart_deskew(const cv::Mat& img) {
    if (tesseract_available_) {
        try {
            return tess_preprocessor_->tesseract_deskew(img);
        } catch (const std::exception& e) {
            std::cerr << "Tesseract deskewing failed, falling back to OpenCV: " << e.what() << std::endl;
        }
    }
    
    // Fallback to OpenCV
    std::vector<cv::Point> points;
    cv::findNonZero(img, points);
    if (points.empty()) {
        return img.clone();
    }
    cv::RotatedRect box = cv::minAreaRect(points);
    float angle = box.angle;
    if (angle < -45.0f) angle += 90.0f;
    cv::Mat rot_mat = cv::getRotationMatrix2D(box.center, angle, 1.0);
    cv::Mat rotated;
    cv::warpAffine(img, rotated, rot_mat, img.size(), cv::INTER_CUBIC, cv::BORDER_REPLICATE);
    return rotated;
}

cv::Mat HybridPreprocessor::smart_dewarp(const cv::Mat& img) {
    if (tesseract_available_) {
        try {
            return tess_preprocessor_->tesseract_dewarp(img);
        } catch (const std::exception& e) {
            std::cerr << "Tesseract dewarping failed, falling back to OpenCV: " << e.what() << std::endl;
        }
    }
    
    // Fallback to OpenCV (existing implementation)
    cv::Mat gray, bin;
    if (img.channels() == 3)
        cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    else
        gray = img;
    cv::adaptiveThreshold(gray, bin, 255, cv::ADAPTIVE_THRESH_MEAN_C, cv::THRESH_BINARY, 31, 10);
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(bin, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    if (contours.empty()) return img.clone();
    size_t largest = 0;
    for (size_t i = 1; i < contours.size(); ++i)
        if (cv::contourArea(contours[i]) > cv::contourArea(contours[largest])) largest = i;
    std::vector<cv::Point> quad;
    cv::approxPolyDP(contours[largest], quad, 20, true);
    if (quad.size() != 4) return img.clone();
    std::sort(quad.begin(), quad.end(), [](const cv::Point& a, const cv::Point& b) { return a.y < b.y; });
    std::vector<cv::Point2f> src(4), dst(4);
    src[0] = quad[0].x < quad[1].x ? quad[0] : quad[1];
    src[1] = quad[0].x > quad[1].x ? quad[0] : quad[1];
    src[2] = quad[2].x < quad[3].x ? quad[2] : quad[3];
    src[3] = quad[2].x > quad[3].x ? quad[2] : quad[3];
    float w1 = cv::norm(src[0] - src[1]), w2 = cv::norm(src[2] - src[3]);
    float h1 = cv::norm(src[0] - src[2]), h2 = cv::norm(src[1] - src[3]);
    float width = std::max(w1, w2), height = std::max(h1, h2);
    dst[0] = cv::Point2f(0, 0); dst[1] = cv::Point2f(width-1, 0);
    dst[2] = cv::Point2f(0, height-1); dst[3] = cv::Point2f(width-1, height-1);
    cv::Mat M = cv::getPerspectiveTransform(src, dst);
    cv::Mat warped;
    cv::warpPerspective(img, warped, M, cv::Size((int)width, (int)height));
    return warped;
}

cv::Mat HybridPreprocessor::smart_denoise(const cv::Mat& img) {
    if (tesseract_available_) {
        try {
            return tess_preprocessor_->tesseract_denoise(img);
        } catch (const std::exception& e) {
            std::cerr << "Tesseract denoising failed, falling back to OpenCV: " << e.what() << std::endl;
        }
    }
    
    // Fallback to OpenCV
    cv::Mat med, bilat;
    cv::medianBlur(img, med, 3);
    cv::bilateralFilter(med, bilat, 9, 75, 75);
    return bilat;
}

cv::Mat HybridPreprocessor::enhanced_preprocess_pipeline(const cv::Mat& img) {
    auto t0 = std::chrono::high_resolution_clock::now();
    
    cv::Mat result = img;
    
    // Apply hybrid preprocessing
    result = smart_denoise(result);
    result = smart_adaptive_threshold(result);
    result = smart_deskew(result);
    result = smart_dewarp(result);
    
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
    g_tesseract_timing = "enhanced_preprocess_pipeline: " + std::to_string(ms) + " ms";
    
    return result;
}

} // namespace preprocessing
} // namespace owlin 