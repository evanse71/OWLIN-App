#pragma once
#include <opencv2/opencv.hpp>
#include <vector>
#include <string>

namespace owlin {
namespace layout {

/**
 * Detect text blocks in a preprocessed (binary or grayscale) image.
 * Returns a vector of bounding rectangles (cv::Rect).
 * Integration: Call after preprocessing, before recognition.
 */
std::vector<cv::Rect> detect_text_blocks(const cv::Mat& preprocessed_img);

/**
 * Detect text lines in a preprocessed (binary or grayscale) image.
 * Returns a vector of bounding rectangles (cv::Rect).
 * Integration: Can be used for line-level recognition.
 */
std::vector<cv::Rect> detect_text_lines(const cv::Mat& preprocessed_img);

/**
 * Draw bounding boxes on an image for visualization.
 * Returns a copy of the image with rectangles drawn.
 */
cv::Mat draw_bounding_boxes(const cv::Mat& img, const std::vector<cv::Rect>& boxes, const cv::Scalar& color = cv::Scalar(0,255,0), int thickness = 2);

/**
 * Demo function: runs block and line detection, draws boxes, and shows the result.
 * For development/testing only.
 */
void demo_layout_analysis(const std::string& image_path);

} // namespace layout
} // namespace owlin 