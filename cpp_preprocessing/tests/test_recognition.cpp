#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include "../recognition/recognition.h"
#include <opencv2/imgcodecs.hpp>

using namespace owlin::recognition;

TEST_CASE("Recognition: valid grayscale image returns text") {
    cv::Mat img = cv::imread("../tests/mock_invoice_line.png", cv::IMREAD_GRAYSCALE);
    REQUIRE(!img.empty());
    OcrRecognizer ocr;
    std::string text, err;
    double conf = 0.0;
    bool ok = ocr.recognize(img, text, conf, err);
    REQUIRE(ok);
    REQUIRE(!text.empty());
    REQUIRE(conf > 0.0);
}

TEST_CASE("Recognition: invalid input returns error") {
    cv::Mat empty;
    OcrRecognizer ocr;
    std::string text, err;
    double conf = 0.0;
    bool ok = ocr.recognize(empty, text, conf, err);
    REQUIRE_FALSE(ok);
    REQUIRE(!err.empty());
} 