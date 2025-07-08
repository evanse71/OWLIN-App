#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include "../preprocess_c_api.h"
#include "../recognition/recognition_c_api.h"
#include "../segmentation/segmentation_c_api.h"
#include <opencv2/imgcodecs.hpp>

TEST_CASE("C API: preprocess_image valid/invalid") {
    int w=0, h=0, c=0;
    unsigned char* buf = nullptr;
    int err = preprocess_image("../tests/mock_invoice.png", &w, &h, &c, &buf);
    REQUIRE(err == 0);
    REQUIRE(buf != nullptr);
    owlin_free(buf);
    err = preprocess_image("does_not_exist.png", &w, &h, &c, &buf);
    REQUIRE(err != 0);
    REQUIRE(buf == nullptr);
    REQUIRE(std::string(owlin_get_last_error()).find("not found") != std::string::npos);
}

TEST_CASE("C API: ocr_recognize valid/invalid") {
    OcrRecognizer* ocr = ocr_create("eng");
    REQUIRE(ocr);
    cv::Mat img = cv::imread("../tests/mock_invoice_line.png", cv::IMREAD_GRAYSCALE);
    REQUIRE(!img.empty());
    char* text = nullptr;
    double conf = 0.0;
    int err = ocr_recognize(ocr, img.data, img.cols, img.rows, 1, &text, &conf);
    REQUIRE(err == 0);
    REQUIRE(text != nullptr);
    owlin_free(text);
    err = ocr_recognize(ocr, nullptr, 0, 0, 1, &text, &conf);
    REQUIRE(err != 0);
    ocr_destroy(ocr);
}

TEST_CASE("C API: ocr_recognize_batch valid") {
    OcrRecognizer* ocr = ocr_create("eng");
    REQUIRE(ocr);
    cv::Mat img = cv::imread("../tests/mock_invoice_line.png", cv::IMREAD_GRAYSCALE);
    REQUIRE(!img.empty());
    const unsigned char* imgs[2] = {img.data, img.data};
    int ws[2] = {img.cols, img.cols};
    int hs[2] = {img.rows, img.rows};
    int cs[2] = {1, 1};
    char** texts = nullptr;
    double* confs = nullptr;
    char** errs = nullptr;
    int err = ocr_recognize_batch(ocr, imgs, ws, hs, cs, 2, &texts, &confs, &errs);
    REQUIRE(err == 0);
    for (int i = 0; i < 2; ++i) {
        REQUIRE(texts[i] != nullptr);
        REQUIRE(confs[i] > 0.0);
        owlin_free(texts[i]);
        owlin_free(errs[i]);
    }
    owlin_free(texts);
    owlin_free(confs);
    owlin_free(errs);
    ocr_destroy(ocr);
}

TEST_CASE("C API: segmentation valid/invalid") {
    Segmenter* seg = segmenter_create();
    REQUIRE(seg);
    cv::Mat img = cv::imread("../tests/mock_invoice.png", cv::IMREAD_GRAYSCALE);
    REQUIRE(!img.empty());
    int* boxes = nullptr;
    int count = 0;
    int err = segment_lines(seg, img.data, img.cols, img.rows, 1, &boxes, &count);
    REQUIRE(err == 0);
    if (count > 0) REQUIRE(boxes != nullptr);
    if (boxes) owlin_free(boxes);
    err = segment_lines(seg, nullptr, 0, 0, 1, &boxes, &count);
    REQUIRE(err != 0);
    segmenter_destroy(seg);
} 