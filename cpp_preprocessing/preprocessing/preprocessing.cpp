#include "preprocessing.h"
#include "tesseract_preprocessing.h"
#include <iostream>
#include <vector>
#include <chrono>
#include <omp.h>
static thread_local std::string g_last_timing;

namespace owlin {
namespace preprocessing {

// Global hybrid preprocessor instance
static std::unique_ptr<HybridPreprocessor> g_hybrid_preprocessor;

// Initialize hybrid preprocessor (lazy initialization)
static HybridPreprocessor* get_hybrid_preprocessor() {
    if (!g_hybrid_preprocessor) {
        g_hybrid_preprocessor = std::make_unique<HybridPreprocessor>();
    }
    return g_hybrid_preprocessor.get();
}

// Print image info (dimensions and channels)
static void print_image_info(const cv::Mat& img, const std::string& label) {
    std::cout << label << ": " << img.cols << " x " << img.rows << " (channels: " << img.channels() << ")\n";
}

cv::Mat load_image(const std::string& path) {
    cv::Mat img = cv::imread(path, cv::IMREAD_COLOR);
    if (img.empty()) {
        throw std::runtime_error("Failed to load image: " + path);
    }
    print_image_info(img, "Loaded image");
    return img;
}

cv::Mat to_grayscale(const cv::Mat& img) {
    cv::Mat gray;
    cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    print_image_info(gray, "Grayscale image");
    return gray;
}

cv::Mat resize_image(const cv::Mat& img, double scale) {
    cv::Mat resized;
    cv::resize(img, resized, cv::Size(), scale, scale, cv::INTER_CUBIC);
    print_image_info(resized, "Resized image");
    return resized;
}

cv::Mat adaptive_gaussian_threshold(const cv::Mat& img) {
    cv::Mat thresh;
    cv::adaptiveThreshold(
        img, thresh,
        255,
        cv::ADAPTIVE_THRESH_GAUSSIAN_C,
        cv::THRESH_BINARY,
        31, // block size
        10  // C value
    );
    print_image_info(thresh, "Adaptive Gaussian Thresholded image");
    return thresh;
}

cv::Mat deskew(const cv::Mat& bin_img) {
    std::vector<cv::Point> points;
    cv::findNonZero(bin_img, points);
    if (points.empty()) {
        std::cout << "Deskew: No nonzero pixels found, skipping.\n";
        return bin_img.clone();
    }
    cv::RotatedRect box = cv::minAreaRect(points);
    float angle = box.angle;
    if (angle < -45.0f) angle += 90.0f;
    cv::Mat rot_mat = cv::getRotationMatrix2D(box.center, angle, 1.0);
    cv::Mat rotated;
    cv::warpAffine(bin_img, rotated, rot_mat, bin_img.size(), cv::INTER_CUBIC, cv::BORDER_REPLICATE);
    print_image_info(rotated, "Deskewed image");
    return rotated;
}

cv::Mat dewarp(const cv::Mat& img) {
    // Simple dewarping: find largest contour, warp to rectangle
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
    src[0] = quad[0].x < quad[1].x ? quad[0] : quad[1]; // top-left
    src[1] = quad[0].x > quad[1].x ? quad[0] : quad[1]; // top-right
    src[2] = quad[2].x < quad[3].x ? quad[2] : quad[3]; // bottom-left
    src[3] = quad[2].x > quad[3].x ? quad[2] : quad[3]; // bottom-right
    float w1 = cv::norm(src[0] - src[1]), w2 = cv::norm(src[2] - src[3]);
    float h1 = cv::norm(src[0] - src[2]), h2 = cv::norm(src[1] - src[3]);
    float width = std::max(w1, w2), height = std::max(h1, h2);
    dst[0] = cv::Point2f(0, 0); dst[1] = cv::Point2f(width-1, 0);
    dst[2] = cv::Point2f(0, height-1); dst[3] = cv::Point2f(width-1, height-1);
    cv::Mat M = cv::getPerspectiveTransform(src, dst);
    cv::Mat warped;
    cv::warpPerspective(img, warped, M, cv::Size((int)width, (int)height));
    print_image_info(warped, "Dewarped image");
    return warped;
}

cv::Mat remove_background(const cv::Mat& img) {
    // Use adaptive thresholding and morphological opening to remove background
    cv::Mat gray, bin, morph;
    if (img.channels() == 3)
        cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    else
        gray = img;
    cv::adaptiveThreshold(gray, bin, 255, cv::ADAPTIVE_THRESH_MEAN_C, cv::THRESH_BINARY, 31, 15);
    cv::morphologyEx(bin, morph, cv::MORPH_OPEN, cv::getStructuringElement(cv::MORPH_RECT, cv::Size(3,3)));
    print_image_info(morph, "Background removed image");
    return morph;
}

cv::Mat auto_orient(const cv::Mat& img) {
    // Use text orientation detection (simple: check horizontal/vertical projection)
    cv::Mat gray;
    if (img.channels() == 3)
        cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    else
        gray = img;
    cv::Mat bin;
    cv::threshold(gray, bin, 0, 255, cv::THRESH_BINARY | cv::THRESH_OTSU);
    cv::Mat hor_proj, ver_proj;
    cv::reduce(bin, hor_proj, 1, cv::REDUCE_SUM, CV_32S);
    cv::reduce(bin, ver_proj, 0, cv::REDUCE_SUM, CV_32S);
    double hor_var = cv::mean((hor_proj - cv::mean(hor_proj)[0]).mul(hor_proj - cv::mean(hor_proj)[0]))[0];
    double ver_var = cv::mean((ver_proj - cv::mean(ver_proj)[0]).mul(ver_proj - cv::mean(ver_proj)[0]))[0];
    if (ver_var > hor_var) {
        // Likely needs 90-degree rotation
        cv::Mat rot;
        cv::rotate(img, rot, cv::ROTATE_90_CLOCKWISE);
        print_image_info(rot, "Auto-oriented image (rotated)");
        return rot;
    }
    print_image_info(img, "Auto-oriented image (no rotation)");
    return img.clone();
}

cv::Mat invoice_denoise(const cv::Mat& img) {
    // Use a combination of median and bilateral filters
    cv::Mat med, bilat;
    cv::medianBlur(img, med, 3);
    cv::bilateralFilter(med, bilat, 9, 75, 75);
    print_image_info(bilat, "Denoised image");
    return bilat;
}

cv::Mat preprocess_pipeline(const std::string& path) {
    auto t0 = std::chrono::high_resolution_clock::now();
    cv::Mat img = load_image(path);
    cv::Mat gray = to_grayscale(img);
    cv::Mat resized = resize_image(gray);
    cv::Mat thresh = adaptive_gaussian_threshold(resized);
    cv::Mat deskewed = deskew(thresh);
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
    g_last_timing = "preprocess_pipeline: " + std::to_string(ms) + " ms";
    return deskewed;
}

// --- NEW: Enhanced Preprocessing Functions ---

cv::Mat enhanced_preprocess_pipeline(const std::string& path) {
    auto t0 = std::chrono::high_resolution_clock::now();
    
    // Load image
    cv::Mat img = load_image(path);
    
    // Apply enhanced preprocessing
    cv::Mat result = enhanced_preprocess_image(img);
    
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
    g_last_timing = "enhanced_preprocess_pipeline: " + std::to_string(ms) + " ms";
    
    return result;
}

cv::Mat enhanced_preprocess_image(const cv::Mat& img) {
    // Convert to grayscale if needed
    cv::Mat gray = img;
    if (img.channels() == 3) {
        gray = to_grayscale(img);
    }
    
    // Resize for better processing
    cv::Mat resized = resize_image(gray);
    
    // Use hybrid preprocessor (Tesseract + OpenCV fallback)
    HybridPreprocessor* preprocessor = get_hybrid_preprocessor();
    cv::Mat result = preprocessor->enhanced_preprocess_pipeline(resized);
    
    print_image_info(result, "Enhanced preprocessed image");
    return result;
}

std::string get_tesseract_timing() {
    // This would return timing from the Tesseract preprocessor
    // For now, return the general timing
    return g_last_timing;
}

bool is_tesseract_preprocessing_available() {
    try {
        HybridPreprocessor* preprocessor = get_hybrid_preprocessor();
        // The hybrid preprocessor will handle availability checking internally
        return true; // If we can create the preprocessor, Tesseract is available
    } catch (const std::exception& e) {
        std::cerr << "Tesseract preprocessing not available: " << e.what() << std::endl;
        return false;
    }
}

} // namespace preprocessing
} // namespace owlin

#ifdef OWLIN_PREPROCESSING_TEST_MAIN
int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <image_path>\n";
        return 1;
    }
    try {
        // Test both pipelines
        std::cout << "=== Testing Original Pipeline ===" << std::endl;
        cv::Mat result1 = owlin::preprocessing::preprocess_pipeline(argv[1]);
        
        std::cout << "\n=== Testing Enhanced Pipeline ===" << std::endl;
        cv::Mat result2 = owlin::preprocessing::enhanced_preprocess_pipeline(argv[1]);
        
        // Show results
        cv::imshow("Original Pipeline Result", result1);
        cv::imshow("Enhanced Pipeline Result", result2);
        std::cout << "Press any key in the image window to exit...\n";
        cv::waitKey(0);
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << std::endl;
        return 2;
    }
    return 0;
}
#endif 