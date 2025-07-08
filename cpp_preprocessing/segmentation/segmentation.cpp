#include "segmentation.h"
#include <opencv2/imgproc.hpp>
#include <algorithm>
#include <chrono>
#include <omp.h>
static thread_local std::string g_last_timing;

namespace owlin {
namespace segmentation {

Segmenter::Segmenter() {}
Segmenter::~Segmenter() {}

std::vector<Box> Segmenter::segment_lines(const cv::Mat& img, std::string& err_msg) {
    std::vector<Box> boxes;
    if (img.empty() || img.channels() != 1) {
        err_msg = "Input image must be non-empty and grayscale";
        return boxes;
    }
    // 1. Binarize (Otsu)
    cv::Mat bin;
    cv::threshold(img, bin, 0, 255, cv::THRESH_BINARY_INV | cv::THRESH_OTSU);

    // 2. Compute horizontal projection profile
    std::vector<int> proj(bin.rows, 0);
    for (int y = 0; y < bin.rows; ++y)
        proj[y] = cv::countNonZero(bin.row(y));

    // 3. Find line regions by thresholding projection
    int min_line_height = 8, min_line_sum = bin.cols / 20;
    bool in_line = false;
    int y0 = 0;
    for (int y = 0; y < bin.rows; ++y) {
        if (proj[y] > min_line_sum) {
            if (!in_line) { y0 = y; in_line = true; }
        } else {
            if (in_line) {
                int y1 = y - 1;
                if (y1 - y0 + 1 >= min_line_height) {
                    int x_min = bin.cols, x_max = 0;
                    for (int yy = y0; yy <= y1; ++yy) {
                        cv::Mat row = bin.row(yy);
                        cv::Mat nonzero;
                        cv::findNonZero(row, nonzero);
                        if (!nonzero.empty()) {
                            int x0 = nonzero.at<cv::Point>(0).x;
                            int x1 = nonzero.at<cv::Point>(nonzero.total() - 1).x;
                            x_min = std::min(x_min, x0);
                            x_max = std::max(x_max, x1);
                        }
                    }
                    if (x_max > x_min)
                        boxes.push_back({x_min, y0, x_max - x_min + 1, y1 - y0 + 1});
                }
                in_line = false;
            }
        }
    }
    err_msg.clear();
    return boxes;
}

std::vector<Box> Segmenter::segment_words(const cv::Mat& img, std::string& err_msg) {
    std::vector<Box> boxes;
    if (img.empty() || img.channels() != 1) {
        err_msg = "Input image must be non-empty and grayscale";
        return boxes;
    }
    cv::Mat bin;
    cv::threshold(img, bin, 0, 255, cv::THRESH_BINARY_INV | cv::THRESH_OTSU);
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(bin, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    for (const auto& c : contours) {
        cv::Rect r = cv::boundingRect(c);
        if (r.width > 5 && r.height > 5) // filter noise
            boxes.push_back({r.x, r.y, r.width, r.height});
    }
    err_msg.clear();
    return boxes;
}

std::vector<ScoredBox> Segmenter::segment_with_confidence(const cv::Mat& img, std::string& err_msg) {
    std::vector<ScoredBox> scored;
    std::vector<Box> lines = segment_lines(img, err_msg);
    if (!err_msg.empty()) return scored;
    for (const auto& line : lines) {
        cv::Mat roi = img(cv::Rect(line.x, line.y, line.w, line.h));
        // Confidence: ratio of nonzero pixels to area
        cv::Mat bin;
        cv::threshold(roi, bin, 0, 255, cv::THRESH_BINARY_INV | cv::THRESH_OTSU);
        double conf = (double)cv::countNonZero(bin) / (bin.rows * bin.cols);
        scored.push_back({line, conf});
    }
    err_msg.clear();
    return scored;
}

std::vector<std::vector<Box>> Segmenter::segment_batch(const std::vector<cv::Mat>& imgs, std::vector<std::string>& out_errors) {
    auto t0 = std::chrono::high_resolution_clock::now();
    std::vector<std::vector<Box>> results(imgs.size());
    out_errors.resize(imgs.size());
    #pragma omp parallel for
    for (int i = 0; i < static_cast<int>(imgs.size()); ++i) {
        std::string err;
        results[i] = segment_lines(imgs[i], err);
        out_errors[i] = err;
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
    g_last_timing = "segment_batch: " + std::to_string(ms) + " ms";
    return results;
}

} // namespace segmentation
} // namespace owlin 