#include "owlin_ocr_c_api.h"
#include <opencv2/opencv.hpp>
#include <cstdlib>
#include <cstring>
#include <string>
#include <exception>
#include <iostream>

// Include modular pipeline headers
your include path may vary:
#include "../preprocessing/preprocessing.h"
#include "../recognition/recognition.h"
#include "../postprocessing/postprocessing.h"

extern "C" {

static const char* owlin_ocr_err_msgs[] = {
    "Success",
    "Unknown error",
    "File not found",
    "Preprocessing error",
    "OCR error"
};

const char* owlin_ocr_strerror(int errcode) {
    if (errcode >= 0 && errcode <= 4) return owlin_ocr_err_msgs[errcode];
    return "Unknown error code";
}

void owlin_ocr_free(void* ptr) {
    if (ptr) std::free(ptr);
}

int owlin_ocr_from_file(const char* filepath, char** out_text_ptr, double* out_confidence) {
    if (!filepath || !out_text_ptr || !out_confidence) return OWLIN_OCR_ERR_UNKNOWN;
    try {
        // Preprocessing
        cv::Mat pre = owlin::preprocessing::preprocess_pipeline(filepath);
        if (pre.empty()) return OWLIN_OCR_ERR_PREPROCESS;
        // Recognition
        auto rec = owlin::recognition::recognize_text(pre);
        // Postprocessing (optional: filter, spellcheck, parse fields)
        std::string text = owlin::postprocessing::spellcheck_corrections(rec.first);
        // Allocate and copy result
        *out_text_ptr = (char*)std::malloc(text.size() + 1);
        if (!*out_text_ptr) return OWLIN_OCR_ERR_UNKNOWN;
        std::memcpy(*out_text_ptr, text.c_str(), text.size() + 1);
        *out_confidence = rec.second;
        return OWLIN_OCR_SUCCESS;
    } catch (const std::exception& ex) {
        std::cerr << "owlin_ocr_from_file error: " << ex.what() << std::endl;
        return OWLIN_OCR_ERR_UNKNOWN;
    }
}

int owlin_ocr_from_buffer(const unsigned char* buffer, int width, int height, int channels, char** out_text_ptr, double* out_confidence) {
    if (!buffer || width <= 0 || height <= 0 || !out_text_ptr || !out_confidence) return OWLIN_OCR_ERR_UNKNOWN;
    try {
        cv::Mat img(height, width, (channels == 1 ? CV_8U : CV_8UC3), (void*)buffer);
        // Preprocessing (skip load, start from grayscale)
        cv::Mat pre = img;
        if (channels != 1) pre = owlin::preprocessing::to_grayscale(img);
        pre = owlin::preprocessing::resize_image(pre);
        pre = owlin::preprocessing::adaptive_gaussian_threshold(pre);
        pre = owlin::preprocessing::deskew(pre);
        // Recognition
        auto rec = owlin::recognition::recognize_text(pre);
        std::string text = owlin::postprocessing::spellcheck_corrections(rec.first);
        *out_text_ptr = (char*)std::malloc(text.size() + 1);
        if (!*out_text_ptr) return OWLIN_OCR_ERR_UNKNOWN;
        std::memcpy(*out_text_ptr, text.c_str(), text.size() + 1);
        *out_confidence = rec.second;
        return OWLIN_OCR_SUCCESS;
    } catch (const std::exception& ex) {
        std::cerr << "owlin_ocr_from_buffer error: " << ex.what() << std::endl;
        return OWLIN_OCR_ERR_UNKNOWN;
    }
}

} // extern "C" 