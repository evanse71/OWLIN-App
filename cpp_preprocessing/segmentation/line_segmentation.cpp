#include "line_segmentation.h"
#include <opencv2/opencv.hpp>
#include <iostream>
#include <stdexcept>

namespace owlin {
namespace segmentation {

std::vector<cv::Rect> segment_lines(const cv::Mat& bin_img) {
    if (bin_img.empty() || bin_img.type() != CV_8UC1) {
        throw std::invalid_argument("Input image must be a non-empty binary (CV_8UC1) image.");
    }
    std::vector<cv::Rect> lines;
    // Horizontal projection profile
    cv::Mat proj;
    cv::reduce(bin_img, proj, 1, cv::REDUCE_SUM, CV_32S);
    int threshold = 10 * 255; // Minimum sum to consider as text (tune as needed)
    int in_line = false, start = 0;
    for (int y = 0; y < proj.rows; ++y) {
        int val = proj.at<int>(y, 0);
        if (!in_line && val > threshold) {
            in_line = true;
            start = y;
        } else if (in_line && val <= threshold) {
            in_line = false;
            int end = y;
            // Find bounding box in this band
            cv::Mat row_band = bin_img.rowRange(start, end);
            std::vector<std::vector<cv::Point>> contours;
            cv::findContours(row_band, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
            if (!contours.empty()) {
                cv::Rect bbox = cv::boundingRect(contours[0]);
                for (size_t i = 1; i < contours.size(); ++i) {
                    bbox |= cv::boundingRect(contours[i]);
                }
                bbox.y += start;
                lines.push_back(bbox);
            }
        }
    }
    std::cout << "Detected " << lines.size() << " text lines." << std::endl;
    return lines;
}

} // namespace segmentation
} // namespace owlin

#ifdef OWLIN_LINE_SEGMENTATION_CLI
#include "../preprocessing/preprocessing.h"
int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <image_path>" << std::endl;
        return 1;
    }
    std::string img_path = argv[1];
    try {
        cv::Mat img = owlin::preprocessing::load_image(img_path);
        cv::Mat gray = owlin::preprocessing::to_grayscale(img);
        cv::Mat bin = owlin::preprocessing::adaptive_gaussian_threshold(gray);
        auto lines = owlin::segmentation::segment_lines(bin);
        cv::Mat vis;
        cv::cvtColor(bin, vis, cv::COLOR_GRAY2BGR);
        for (const auto& rect : lines) {
            cv::rectangle(vis, rect, cv::Scalar(0,0,255), 2);
        }
        cv::imshow("Lines", vis);
        cv::waitKey(0);
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}
#endif 