#pragma once
#include <string>
#include <vector>
#include <utility>
#include <map>

namespace owlin {
namespace postprocessing {

/**
 * Filter recognized OCR results by confidence threshold.
 * Input: vector of (string, confidence) pairs.
 * Output: filtered vector.
 */
std::vector<std::pair<std::string, double>> filter_by_confidence(const std::vector<std::pair<std::string, double>>& results, double threshold = 0.7);

/**
 * Run spellcheck/dictionary correction on recognized text.
 * Input: string, Output: corrected string.
 * (Stub: can use SymSpell or similar in future.)
 */
std::string spellcheck_corrections(const std::string& text);

/**
 * Extract key invoice fields (number, date, totals) using regex parsing.
 * Returns a map of field name to value.
 */
std::map<std::string, std::string> extract_invoice_fields(const std::string& ocr_text);

/**
 * Unit test: verify field extraction on sample invoice text.
 */
void test_invoice_field_extraction();

} // namespace postprocessing
} // namespace owlin 