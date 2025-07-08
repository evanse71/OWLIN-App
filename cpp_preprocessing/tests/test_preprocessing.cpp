#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include "../preprocessing/preprocessing.h"
#include <opencv2/imgcodecs.hpp>

using namespace owlin::preprocessing;

TEST_CASE("Preprocessing: grayscale conversion") {
    cv::Mat color = cv::imread("../tests/mock_invoice_color.png");
    REQUIRE(!color.empty());
    cv::Mat gray = to_grayscale(color);
    REQUIRE(gray.channels() == 1);
}

TEST_CASE("Preprocessing: denoising") {
    cv::Mat img = cv::imread("../tests/mock_invoice_noisy.png", cv::IMREAD_GRAYSCALE);
    REQUIRE(!img.empty());
    cv::Mat denoised = invoice_denoise(img);
    REQUIRE(denoised.size() == img.size());
}

TEST_CASE("Preprocessing: dewarping") {
    cv::Mat img = cv::imread("../tests/mock_invoice_skewed.png");
    REQUIRE(!img.empty());
    cv::Mat dewarped = dewarp(img);
    REQUIRE(dewarped.size().area() > 0);
}

TEST_CASE("Preprocessing: background removal") {
    cv::Mat img = cv::imread("../tests/mock_invoice_bg.png");
    REQUIRE(!img.empty());
    cv::Mat clean = remove_background(img);
    REQUIRE(clean.size() == img.size());
}

TEST_CASE("Preprocessing: auto-orient") {
    cv::Mat img = cv::imread("../tests/mock_invoice_rotated.png");
    REQUIRE(!img.empty());
    cv::Mat oriented = auto_orient(img);
    REQUIRE(oriented.size() == img.size());
} 