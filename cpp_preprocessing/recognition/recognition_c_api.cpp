#include "recognition_c_api.h"
#include "recognition.h"
#include <cstring>
#include <exception>
#include <string>

using namespace owlin::recognition;

struct OcrRecognizerImpl {
    OcrRecognizer* recognizer;
    std::string last_error;
};

static thread_local std::string g_last_error;
static thread_local std::string g_last_timing;

extern "C" {

OcrRecognizer* ocr_create(const char* lang) {
    try {
        auto* impl = new OcrRecognizerImpl;
        impl->recognizer = new OcrRecognizer(lang ? lang : "eng");
        impl->last_error.clear();
        return impl;
    } catch (const std::exception& ex) {
        g_last_error = ex.what();
        return nullptr;
    }
}

void ocr_destroy(OcrRecognizer* ocr) {
    if (ocr) {
        delete ocr->recognizer;
        delete ocr;
    }
}

int ocr_recognize(OcrRecognizer* ocr, const unsigned char* img, int width, int height, int channels, char** out_text, double* out_confidence) {
    if (!ocr || !img || width <= 0 || height <= 0 || channels != 1 || !out_text || !out_confidence) {
        g_last_error = "Invalid arguments to ocr_recognize";
        if (out_text) *out_text = nullptr;
        if (out_confidence) *out_confidence = 0.0;
        return 1;
    }
    try {
        cv::Mat mat(height, width, CV_8UC1, const_cast<unsigned char*>(img));
        std::string text, err;
        double conf = 0.0;
        if (!ocr->recognizer->recognize(mat, text, conf, err)) {
            g_last_error = err;
            *out_text = nullptr;
            *out_confidence = 0.0;
            return 2;
        }
        *out_text = (char*)malloc(text.size() + 1);
        std::memcpy(*out_text, text.c_str(), text.size() + 1);
        *out_confidence = conf;
        g_last_error.clear();
        return 0;
    } catch (const std::exception& ex) {
        g_last_error = ex.what();
        if (out_text) *out_text = nullptr;
        if (out_confidence) *out_confidence = 0.0;
        return 3;
    }
}

int ocr_recognize_batch(OcrRecognizer* ocr, const unsigned char** imgs, const int* widths, const int* heights, const int* channels, int n_images, char*** out_texts, double** out_confidences, char*** out_errors) {
    if (!ocr || !imgs || !widths || !heights || !channels || n_images <= 0 || !out_texts || !out_confidences || !out_errors) {
        g_last_error = "Invalid arguments to ocr_recognize_batch";
        if (out_texts) *out_texts = nullptr;
        if (out_confidences) *out_confidences = nullptr;
        if (out_errors) *out_errors = nullptr;
        return 1;
    }
    try {
        std::vector<cv::Mat> images;
        for (int i = 0; i < n_images; ++i) {
            if (!imgs[i] || widths[i] <= 0 || heights[i] <= 0 || channels[i] != 1) {
                g_last_error = "Invalid image in batch at index " + std::to_string(i);
                *out_texts = nullptr; *out_confidences = nullptr; *out_errors = nullptr;
                return 2;
            }
            images.emplace_back(heights[i], widths[i], CV_8UC1, const_cast<unsigned char*>(imgs[i]));
        }
        std::vector<std::string> texts, errors;
        std::vector<double> confs;
        bool ok = ocr->recognizer->recognize_batch(images, texts, confs, errors);
        // Allocate output arrays
        *out_texts = (char**)malloc(sizeof(char*) * n_images);
        *out_confidences = (double*)malloc(sizeof(double) * n_images);
        *out_errors = (char**)malloc(sizeof(char*) * n_images);
        for (int i = 0; i < n_images; ++i) {
            (*out_texts)[i] = (char*)malloc(texts[i].size() + 1);
            std::memcpy((*out_texts)[i], texts[i].c_str(), texts[i].size() + 1);
            (*out_confidences)[i] = confs[i];
            (*out_errors)[i] = (char*)malloc(errors[i].size() + 1);
            std::memcpy((*out_errors)[i], errors[i].c_str(), errors[i].size() + 1);
        }
        g_last_error.clear();
        return ok ? 0 : 3;
    } catch (const std::exception& ex) {
        g_last_error = ex.what();
        if (out_texts) *out_texts = nullptr;
        if (out_confidences) *out_confidences = nullptr;
        if (out_errors) *out_errors = nullptr;
        return 4;
    }
}

void owlin_free(void* ptr) {
    if (ptr) free(ptr);
}

const char* owlin_get_last_error() {
    return g_last_error.c_str();
}

const char* ocr_get_last_timing() {
    return g_last_timing.c_str();
}

} // extern "C" 