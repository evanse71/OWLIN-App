#include "recognition.h"
#include <opencv2/opencv.hpp>
#include <tesseract/baseapi.h>
#include <leptonica/allheaders.h>
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <chrono>
#include <omp.h>
static thread_local std::string g_last_timing;

namespace owlin {
namespace recognition {

OcrRecognizer::OcrRecognizer(const std::string& lang) : tess_(nullptr) {
    tess_ = new tesseract::TessBaseAPI();
    if (tess_->Init(nullptr, lang.c_str())) {
        delete tess_;
        tess_ = nullptr;
        throw std::runtime_error("Failed to initialize Tesseract with language: " + lang);
    }
}

OcrRecognizer::~OcrRecognizer() {
    if (tess_) {
        tess_->End();
        delete tess_;
    }
}

bool OcrRecognizer::recognize(const cv::Mat& img, std::string& out_text, double& out_confidence, std::string& err_msg) {
    if (!tess_ || img.empty() || img.channels() != 1) {
        err_msg = "Invalid recognizer or image (must be grayscale)";
        return false;
    }
    tess_->SetImage(img.data, img.cols, img.rows, 1, img.step);
    char* text = tess_->GetUTF8Text();
    if (!text) {
        err_msg = "Tesseract failed to recognize text";
        return false;
    }
    out_text = std::string(text);
    delete[] text;
    out_confidence = tess_->MeanTextConf() / 100.0;
    err_msg.clear();
    return true;
}

bool OcrRecognizer::recognize_batch(const std::vector<cv::Mat>& images, std::vector<std::string>& out_texts, std::vector<double>& out_confidences, std::vector<std::string>& out_errors) {
    auto t0 = std::chrono::high_resolution_clock::now();
    out_texts.resize(images.size());
    out_confidences.resize(images.size());
    out_errors.resize(images.size());
    bool all_ok = true;
    #pragma omp parallel for
    for (int i = 0; i < static_cast<int>(images.size()); ++i) {
        std::string text, err;
        double conf = 0.0;
        bool ok = recognize(images[i], text, conf, err);
        out_texts[i] = text;
        out_confidences[i] = conf;
        out_errors[i] = err;
        if (!ok) all_ok = false;
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
    g_last_timing = "recognize_batch: " + std::to_string(ms) + " ms";
    return all_ok;
}

// Recognize text in a given image region using Tesseract LSTM OCR
std::pair<std::string, double> recognize_text(const cv::Mat& img_region) {
    tesseract::TessBaseAPI tess;
    // Initialize Tesseract with English, OEM LSTM only
    if (tess.Init(nullptr, "eng", tesseract::OEM_LSTM_ONLY) != 0) {
        std::cerr << "Tesseract initialization failed!\n";
        return {"", 0.0};
    }
    tess.SetPageSegMode(tesseract::PSM_AUTO);
    // Convert to 8-bit if needed
    cv::Mat img8u;
    if (img_region.type() != CV_8U) {
        img_region.convertTo(img8u, CV_8U);
    } else {
        img8u = img_region;
    }
    tess.SetImage(img8u.data, img8u.cols, img8u.rows, 1, img8u.step);
    char* out = tess.GetUTF8Text();
    std::string text = out ? std::string(out) : "";
    delete[] out;
    // Confidence: mean over all symbols
    int conf = tess.MeanTextConf();
    double confidence = conf / 100.0;
    tess.End();
    return {text, confidence};
}

// Recognize text in multiple regions
std::vector<std::pair<std::string, double>> recognize_regions(const cv::Mat& img, const std::vector<cv::Rect>& regions) {
    std::vector<std::pair<std::string, double>> results;
    for (const auto& rect : regions) {
        cv::Mat roi = img(rect);
        results.push_back(recognize_text(roi));
    }
    return results;
}

// Demo function: runs recognition on a sample image or regions, prints results
void demo_recognition(const std::string& image_path) {
    cv::Mat img = cv::imread(image_path, cv::IMREAD_GRAYSCALE);
    if (img.empty()) {
        std::cerr << "Failed to load image: " << image_path << std::endl;
        return;
    }
    auto result = recognize_text(img);
    std::cout << "Recognized text:\n" << result.first << std::endl;
    std::cout << "Confidence: " << result.second << std::endl;
}

} // namespace recognition
} // namespace owlin

#ifdef OWLIN_RECOGNITION_TEST_MAIN
int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <image_path>\n";
        return 1;
    }
    owlin::recognition::demo_recognition(argv[1]);
    return 0;
}
#endif 