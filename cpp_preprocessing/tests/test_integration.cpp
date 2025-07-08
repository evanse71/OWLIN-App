#include <iostream>
#include <chrono>
#include "../preprocessing/preprocessing.h"
#include "../recognition/recognition.h"
#include "../postprocessing/postprocessing.h"

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <sample_invoice_image>\n";
        return 1;
    }
    std::string image_path = argv[1];
    try {
        auto start = std::chrono::high_resolution_clock::now();
        // Preprocessing
        cv::Mat pre = owlin::preprocessing::preprocess_pipeline(image_path);
        // Recognition
        auto rec = owlin::recognition::recognize_text(pre);
        // Postprocessing
        std::string text = owlin::postprocessing::spellcheck_corrections(rec.first);
        auto fields = owlin::postprocessing::extract_invoice_fields(text);
        auto end = std::chrono::high_resolution_clock::now();
        double elapsed = std::chrono::duration<double>(end - start).count();
        std::cout << "Recognized text:\n" << text << std::endl;
        std::cout << "Confidence: " << rec.second << std::endl;
        std::cout << "Extracted fields:\n";
        for (const auto& kv : fields) {
            std::cout << "  " << kv.first << ": " << kv.second << std::endl;
        }
        std::cout << "Elapsed time: " << elapsed << " seconds\n";
        // Simple assertions
        if (text.empty()) {
            std::cerr << "FAIL: OCR text is empty!\n";
            return 2;
        }
        if (rec.second < 0.5) {
            std::cerr << "WARN: Low confidence (" << rec.second << ")\n";
        }
        std::cout << "Integration test PASSED\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << std::endl;
        return 3;
    }
} 