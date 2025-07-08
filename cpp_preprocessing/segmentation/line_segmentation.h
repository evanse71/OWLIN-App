#pragma once
#include <opencv2/opencv.hpp>
#include <vector>

namespace owlin {
namespace segmentation {

/**
 * @brief Segment text lines in a binary image using horizontal projection or connected components.
 * @param bin_img Preprocessed binary image (CV_8UC1, 0/255).
 * @return Vector of bounding rectangles for detected text lines.
 */
std::vector<cv::Rect> segment_lines(const cv::Mat& bin_img);

} // namespace segmentation
} // namespace owlin 