#pragma once
#include <opencv2/opencv.hpp>
#include <string>
#include <tesseract/baseapi.h>

namespace owlin {
namespace recognition {

class OcrRecognizer {
public:
    OcrRecognizer(const std::string& lang = "eng");
    ~OcrRecognizer();
    // Recognize text from a grayscale image. Returns true on success.
    bool recognize(const cv::Mat& img, std::string& out_text, double& out_confidence, std::string& err_msg);
    /**
     * Batch recognize text from multiple grayscale images (lines/fields).
     * @param images Vector of grayscale images (CV_8UC1).
     * @param out_texts Output: vector of recognized texts.
     * @param out_confidences Output: vector of confidence scores.
     * @param out_errors Output: vector of error messages (empty if success).
     * @return true if all succeed, false if any fail.
     */
    bool recognize_batch(const std::vector<cv::Mat>& images, std::vector<std::string>& out_texts, std::vector<double>& out_confidences, std::vector<std::string>& out_errors);
private:
    tesseract::TessBaseAPI* tess_;
};

} // namespace recognition
} // namespace owlin
 