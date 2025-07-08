#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include "../segmentation/segmentation.h"
#include <opencv2/imgcodecs.hpp>

using namespace owlin::segmentation;

TEST_CASE("Segmentation: valid image returns bounding boxes") {
    cv::Mat img = cv::imread("../tests/mock_invoice.png", cv::IMREAD_GRAYSCALE);
    REQUIRE(!img.empty());
    Segmenter seg;
    std::string err;
    auto boxes = seg.segment_lines(img, err);
    REQUIRE(err.empty());
    REQUIRE(!boxes.empty());
}

TEST_CASE("Segmentation: empty image returns empty result") {
    cv::Mat empty;
    Segmenter seg;
    std::string err;
    auto boxes = seg.segment_lines(empty, err);
    REQUIRE(!err.empty());
    REQUIRE(boxes.empty());
} 