#include "layout.h"
#include <opencv2/opencv.hpp>
#include <iostream>
#include <algorithm>

namespace owlin {
namespace layout {

// Helper: Print bounding boxes
static void print_boxes(const std::vector<cv::Rect>& boxes, const std::string& label) {
    std::cout << label << ": " << boxes.size() << " regions\n";
    for (size_t i = 0; i < boxes.size(); ++i) {
        std::cout << "  Box " << i << ": x=" << boxes[i].x << ", y=" << boxes[i].y
                  << ", w=" << boxes[i].width << ", h=" << boxes[i].height << "\n";
    }
}

// Detect text blocks using contours (can be improved with morphology)
std::vector<cv::Rect> detect_text_blocks(const cv::Mat& preprocessed_img) {
    std::vector<std::vector<cv::Point>> contours;
    std::vector<cv::Rect> boxes;
    cv::Mat img_bin;
    if (preprocessed_img.channels() == 3)
        cv::cvtColor(preprocessed_img, img_bin, cv::COLOR_BGR2GRAY);
    else
        img_bin = preprocessed_img.clone();
    if (img_bin.type() != CV_8U)
        img_bin.convertTo(img_bin, CV_8U);
    // Find contours (external only)
    cv::findContours(img_bin, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    for (const auto& c : contours) {
        cv::Rect box = cv::boundingRect(c);
        // Filter small regions
        if (box.area() > 100) boxes.push_back(box);
    }
    print_boxes(boxes, "Text blocks");
    return boxes;
}

// Detect text lines using horizontal projection and contours
std::vector<cv::Rect> detect_text_lines(const cv::Mat& preprocessed_img) {
    // For demo: use same as blocks, but could use morphology for lines
    // (e.g., horizontal dilation then contour)
    std::vector<cv::Rect> lines = detect_text_blocks(preprocessed_img);
    print_boxes(lines, "Text lines");
    return lines;
}

// Draw bounding boxes on an image
cv::Mat draw_bounding_boxes(const cv::Mat& img, const std::vector<cv::Rect>& boxes, const cv::Scalar& color, int thickness) {
    cv::Mat out;
    if (img.channels() == 1)
        cv::cvtColor(img, out, cv::COLOR_GRAY2BGR);
    else
        out = img.clone();
    for (const auto& box : boxes) {
        cv::rectangle(out, box, color, thickness);
    }
    return out;
}

// Demo function: load, detect, draw, show
void demo_layout_analysis(const std::string& image_path) {
    cv::Mat img = cv::imread(image_path, cv::IMREAD_GRAYSCALE);
    if (img.empty()) {
        std::cerr << "Failed to load image: " << image_path << std::endl;
        return;
    }
    std::vector<cv::Rect> blocks = detect_text_blocks(img);
    std::vector<cv::Rect> lines = detect_text_lines(img);
    cv::Mat vis = draw_bounding_boxes(img, blocks, cv::Scalar(0,255,0), 2);
    vis = draw_bounding_boxes(vis, lines, cv::Scalar(0,0,255), 1);
    cv::imshow("Layout Analysis Demo", vis);
    std::cout << "Press any key in the image window to exit...\n";
    cv::waitKey(0);
}

} // namespace layout
} // namespace owlin

#ifdef OWLIN_LAYOUT_TEST_MAIN
int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <preprocessed_image_path>\n";
        return 1;
    }
    owlin::layout::demo_layout_analysis(argv[1]);
    return 0;
}
#endif 