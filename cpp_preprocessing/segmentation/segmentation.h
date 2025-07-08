#pragma once
#include <opencv2/core.hpp>
#include <vector>
#include <string>

namespace owlin {
namespace segmentation {

struct Box { int x, y, w, h; };
struct ScoredBox { Box box; double confidence; };

class Segmenter {
public:
    Segmenter();
    ~Segmenter();
    // Detect lines in a grayscale image. Returns vector of bounding boxes.
    std::vector<Box> segment_lines(const cv::Mat& img, std::string& err_msg);
    /**
     * Detect words/fields using connected components analysis.
     * Returns vector of bounding boxes.
     */
    std::vector<Box> segment_words(const cv::Mat& img, std::string& err_msg);
    /**
     * Detect lines/words with confidence scores (projection + CC).
     */
    std::vector<ScoredBox> segment_with_confidence(const cv::Mat& img, std::string& err_msg);
    /**
     * Batch segmentation API: process multiple images (e.g., for multi-column/table layouts).
     * Returns vector of vector of boxes per image.
     */
    std::vector<std::vector<Box>> segment_batch(const std::vector<cv::Mat>& imgs, std::vector<std::string>& out_errors);
};

} // namespace segmentation
} // namespace owlin 