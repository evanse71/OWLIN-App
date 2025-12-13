#include "preprocess_c_api.h"
#include "preprocessing/preprocessing.h"
#include <opencv2/opencv.hpp>
#include <iostream>
#include <cstring>
#include <memory>

// Thread-local error message storage
static thread_local std::string g_last_error;

// Helper function to set error message
static void set_error(const std::string& error) {
    g_last_error = error;
    std::cerr << "[Owlin Preprocess] Error: " << error << std::endl;
}

// Helper function to allocate and copy image data
static unsigned char* copy_image_data(const cv::Mat& img) {
    if (img.empty()) {
        return nullptr;
    }
    
    int img_size = img.total() * img.channels();
    unsigned char* buffer = (unsigned char*)malloc(img_size);
    if (!buffer) {
        set_error("Failed to allocate memory for image buffer");
        return nullptr;
    }
    
    // Copy image data
    if (img.isContinuous()) {
        memcpy(buffer, img.data, img_size);
    } else {
        // Copy row by row if image is not continuous
        for (int i = 0; i < img.rows; ++i) {
            memcpy(buffer + i * img.cols * img.channels(), img.ptr(i), img.cols * img.channels());
        }
    }
    
    return buffer;
}

extern "C" {

int preprocess_image(const char* filepath, int* width, int* height, int* channels, unsigned char** out_buffer) {
    if (!filepath || !width || !height || !channels || !out_buffer) {
        set_error("Invalid arguments to preprocess_image");
        return OWLIN_PREPROCESS_ERR_INVALID_ARG;
    }
    
    *out_buffer = nullptr;
    
    try {
        // Use the original preprocessing pipeline
        cv::Mat result = owlin::preprocessing::preprocess_pipeline(filepath);
        
        if (result.empty()) {
            set_error("Preprocessing failed - empty result");
            return OWLIN_PREPROCESS_ERR_OPENCV;
        }
        
        // Allocate and copy image data
        *out_buffer = copy_image_data(result);
        if (!*out_buffer) {
            return OWLIN_PREPROCESS_ERR_MEMORY;
        }
        
        // Set output dimensions
        *width = result.cols;
        *height = result.rows;
        *channels = result.channels();
        
        std::cout << "[Owlin Preprocess] Original pipeline completed successfully" << std::endl;
        return OWLIN_PREPROCESS_SUCCESS;
        
    } catch (const std::exception& ex) {
        set_error(std::string("Preprocessing failed: ") + ex.what());
        return OWLIN_PREPROCESS_ERR_UNKNOWN;
    }
}

int enhanced_preprocess_image(const char* filepath, int* width, int* height, int* channels, unsigned char** out_buffer) {
    if (!filepath || !width || !height || !channels || !out_buffer) {
        set_error("Invalid arguments to enhanced_preprocess_image");
        return OWLIN_PREPROCESS_ERR_INVALID_ARG;
    }
    
    *out_buffer = nullptr;
    
    try {
        // Use the enhanced preprocessing pipeline (Tesseract + OpenCV fallback)
        cv::Mat result = owlin::preprocessing::enhanced_preprocess_pipeline(filepath);
        
        if (result.empty()) {
            set_error("Enhanced preprocessing failed - empty result");
            return OWLIN_PREPROCESS_ERR_OPENCV;
        }
        
        // Allocate and copy image data
        *out_buffer = copy_image_data(result);
        if (!*out_buffer) {
            return OWLIN_PREPROCESS_ERR_MEMORY;
        }
        
        // Set output dimensions
        *width = result.cols;
        *height = result.rows;
        *channels = result.channels();
        
        std::cout << "[Owlin Preprocess] Enhanced pipeline completed successfully" << std::endl;
        return OWLIN_PREPROCESS_SUCCESS;
        
    } catch (const std::exception& ex) {
        set_error(std::string("Enhanced preprocessing failed: ") + ex.what());
        return OWLIN_PREPROCESS_ERR_UNKNOWN;
    }
}

int enhanced_preprocess_buffer(const unsigned char* input_buffer, int input_width, int input_height, int input_channels,
                              int* width, int* height, int* channels, unsigned char** out_buffer) {
    if (!input_buffer || input_width <= 0 || input_height <= 0 || input_channels <= 0 ||
        !width || !height || !channels || !out_buffer) {
        set_error("Invalid arguments to enhanced_preprocess_buffer");
        return OWLIN_PREPROCESS_ERR_INVALID_ARG;
    }
    
    *out_buffer = nullptr;
    
    try {
        // Create OpenCV Mat from input buffer
        cv::Mat input_img;
        if (input_channels == 1) {
            input_img = cv::Mat(input_height, input_width, CV_8UC1, (void*)input_buffer);
        } else if (input_channels == 3) {
            input_img = cv::Mat(input_height, input_width, CV_8UC3, (void*)input_buffer);
        } else {
            set_error("Unsupported number of input channels");
            return OWLIN_PREPROCESS_ERR_INVALID_ARG;
        }
        
        // Apply enhanced preprocessing
        cv::Mat result = owlin::preprocessing::enhanced_preprocess_image(input_img);
        
        if (result.empty()) {
            set_error("Enhanced preprocessing failed - empty result");
            return OWLIN_PREPROCESS_ERR_OPENCV;
        }
        
        // Allocate and copy image data
        *out_buffer = copy_image_data(result);
        if (!*out_buffer) {
            return OWLIN_PREPROCESS_ERR_MEMORY;
        }
        
        // Set output dimensions
        *width = result.cols;
        *height = result.rows;
        *channels = result.channels();
        
        std::cout << "[Owlin Preprocess] Enhanced buffer preprocessing completed successfully" << std::endl;
        return OWLIN_PREPROCESS_SUCCESS;
        
    } catch (const std::exception& ex) {
        set_error(std::string("Enhanced buffer preprocessing failed: ") + ex.what());
        return OWLIN_PREPROCESS_ERR_UNKNOWN;
    }
}

int is_tesseract_preprocessing_available() {
    try {
        return owlin::preprocessing::is_tesseract_preprocessing_available() ? 1 : 0;
    } catch (const std::exception& ex) {
        set_error(std::string("Error checking Tesseract availability: ") + ex.what());
        return 0;
    }
}

const char* get_preprocessing_timing() {
    try {
        static std::string timing_str = owlin::preprocessing::get_tesseract_timing();
        return timing_str.c_str();
    } catch (const std::exception& ex) {
        set_error(std::string("Error getting timing: ") + ex.what());
        return "Timing not available";
    }
}

const char* owlin_get_last_error() {
    return g_last_error.c_str();
}

} // extern "C" 