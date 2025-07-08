#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include "../preprocessing/tesseract_preprocessing.h"
#include <opencv2/imgcodecs.hpp>
#include <opencv2/core.hpp>

using namespace owlin::preprocessing;

TEST_CASE("TesseractPreprocessor: initialization") {
    SECTION("Should initialize without errors") {
        REQUIRE_NOTHROW(TesseractPreprocessor());
    }
    
    SECTION("Should report availability") {
        TesseractPreprocessor preprocessor;
        // Should be available if Leptonica is installed
        REQUIRE(preprocessor.is_available() == true);
    }
}

TEST_CASE("TesseractPreprocessor: adaptive thresholding") {
    TesseractPreprocessor preprocessor;
    
    SECTION("Should handle empty image") {
        cv::Mat empty;
        cv::Mat result = preprocessor.tesseract_adaptive_threshold(empty);
        REQUIRE(result.empty());
    }
    
    SECTION("Should process valid grayscale image") {
        // Create a simple test image
        cv::Mat test_img(100, 100, CV_8UC1);
        test_img.setTo(128);
        // Add some text-like patterns
        cv::rectangle(test_img, cv::Point(10, 10), cv::Point(90, 30), 255, -1);
        cv::rectangle(test_img, cv::Point(10, 40), cv::Point(90, 60), 0, -1);
        
        cv::Mat result = preprocessor.tesseract_adaptive_threshold(test_img);
        REQUIRE(!result.empty());
        REQUIRE(result.size() == test_img.size());
        REQUIRE(result.type() == CV_8UC1);
    }
}

TEST_CASE("TesseractPreprocessor: deskewing") {
    TesseractPreprocessor preprocessor;
    
    SECTION("Should handle empty image") {
        cv::Mat empty;
        cv::Mat result = preprocessor.tesseract_deskew(empty);
        REQUIRE(result.empty());
    }
    
    SECTION("Should process valid image") {
        // Create a simple test image
        cv::Mat test_img(100, 100, CV_8UC1);
        test_img.setTo(0);
        // Add some horizontal lines (should be easy to deskew)
        cv::line(test_img, cv::Point(10, 20), cv::Point(90, 20), 255, 2);
        cv::line(test_img, cv::Point(10, 40), cv::Point(90, 40), 255, 2);
        cv::line(test_img, cv::Point(10, 60), cv::Point(90, 60), 255, 2);
        
        cv::Mat result = preprocessor.tesseract_deskew(test_img);
        REQUIRE(!result.empty());
        REQUIRE(result.size() == test_img.size());
    }
}

TEST_CASE("TesseractPreprocessor: denoising") {
    TesseractPreprocessor preprocessor;
    
    SECTION("Should handle empty image") {
        cv::Mat empty;
        cv::Mat result = preprocessor.tesseract_denoise(empty);
        REQUIRE(result.empty());
    }
    
    SECTION("Should process noisy image") {
        // Create a noisy test image
        cv::Mat test_img(100, 100, CV_8UC1);
        test_img.setTo(128);
        // Add some text-like patterns
        cv::rectangle(test_img, cv::Point(10, 10), cv::Point(90, 30), 255, -1);
        // Add some noise
        cv::randn(test_img, 128, 50);
        
        cv::Mat result = preprocessor.tesseract_denoise(test_img);
        REQUIRE(!result.empty());
        REQUIRE(result.size() == test_img.size());
    }
}

TEST_CASE("HybridPreprocessor: initialization") {
    SECTION("Should initialize without errors") {
        REQUIRE_NOTHROW(HybridPreprocessor());
    }
}

TEST_CASE("HybridPreprocessor: smart adaptive thresholding") {
    HybridPreprocessor preprocessor;
    
    SECTION("Should handle empty image") {
        cv::Mat empty;
        cv::Mat result = preprocessor.smart_adaptive_threshold(empty);
        REQUIRE(result.empty());
    }
    
    SECTION("Should process valid image with fallback") {
        // Create a simple test image
        cv::Mat test_img(100, 100, CV_8UC1);
        test_img.setTo(128);
        cv::rectangle(test_img, cv::Point(10, 10), cv::Point(90, 30), 255, -1);
        
        cv::Mat result = preprocessor.smart_adaptive_threshold(test_img);
        REQUIRE(!result.empty());
        REQUIRE(result.size() == test_img.size());
        REQUIRE(result.type() == CV_8UC1);
    }
}

TEST_CASE("HybridPreprocessor: smart deskewing") {
    HybridPreprocessor preprocessor;
    
    SECTION("Should handle empty image") {
        cv::Mat empty;
        cv::Mat result = preprocessor.smart_deskew(empty);
        REQUIRE(result.empty());
    }
    
    SECTION("Should process valid image with fallback") {
        // Create a simple test image
        cv::Mat test_img(100, 100, CV_8UC1);
        test_img.setTo(0);
        cv::line(test_img, cv::Point(10, 20), cv::Point(90, 20), 255, 2);
        cv::line(test_img, cv::Point(10, 40), cv::Point(90, 40), 255, 2);
        
        cv::Mat result = preprocessor.smart_deskew(test_img);
        REQUIRE(!result.empty());
        REQUIRE(result.size() == test_img.size());
    }
}

TEST_CASE("HybridPreprocessor: enhanced pipeline") {
    HybridPreprocessor preprocessor;
    
    SECTION("Should handle empty image") {
        cv::Mat empty;
        cv::Mat result = preprocessor.enhanced_preprocess_pipeline(empty);
        REQUIRE(result.empty());
    }
    
    SECTION("Should process valid image through full pipeline") {
        // Create a test image
        cv::Mat test_img(100, 100, CV_8UC1);
        test_img.setTo(128);
        cv::rectangle(test_img, cv::Point(10, 10), cv::Point(90, 30), 255, -1);
        cv::rectangle(test_img, cv::Point(10, 40), cv::Point(90, 60), 0, -1);
        
        cv::Mat result = preprocessor.enhanced_preprocess_pipeline(test_img);
        REQUIRE(!result.empty());
        REQUIRE(result.size() == test_img.size());
        REQUIRE(result.type() == CV_8UC1);
    }
}

TEST_CASE("TesseractPreprocessor: full pipeline") {
    TesseractPreprocessor preprocessor;
    
    SECTION("Should handle empty image") {
        cv::Mat empty;
        cv::Mat result = preprocessor.tesseract_preprocess_pipeline(empty);
        REQUIRE(result.empty());
    }
    
    SECTION("Should process valid image through full Tesseract pipeline") {
        // Create a test image
        cv::Mat test_img(100, 100, CV_8UC1);
        test_img.setTo(128);
        cv::rectangle(test_img, cv::Point(10, 10), cv::Point(90, 30), 255, -1);
        cv::rectangle(test_img, cv::Point(10, 40), cv::Point(90, 60), 0, -1);
        
        cv::Mat result = preprocessor.tesseract_preprocess_pipeline(test_img);
        REQUIRE(!result.empty());
        REQUIRE(result.size() == test_img.size());
        REQUIRE(result.type() == CV_8UC1);
    }
}

TEST_CASE("Error handling and fallback") {
    SECTION("Should handle Tesseract errors gracefully") {
        TesseractPreprocessor preprocessor;
        
        // Test with invalid image data
        cv::Mat invalid_img(0, 0, CV_8UC1);
        cv::Mat result = preprocessor.tesseract_adaptive_threshold(invalid_img);
        REQUIRE(result.empty());
    }
    
    SECTION("Hybrid preprocessor should fallback on Tesseract errors") {
        HybridPreprocessor preprocessor;
        
        // Test with invalid image data - should fallback to OpenCV
        cv::Mat invalid_img(0, 0, CV_8UC1);
        cv::Mat result = preprocessor.smart_adaptive_threshold(invalid_img);
        REQUIRE(result.empty());
    }
} 