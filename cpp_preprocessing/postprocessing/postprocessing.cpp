#include "postprocessing.h"
#include <regex>
#include <iostream>
#include <algorithm>

namespace owlin {
namespace postprocessing {

std::vector<std::pair<std::string, double>> filter_by_confidence(const std::vector<std::pair<std::string, double>>& results, double threshold) {
    std::vector<std::pair<std::string, double>> filtered;
    for (const auto& r : results) {
        if (r.second >= threshold) filtered.push_back(r);
    }
    return filtered;
}

std::string spellcheck_corrections(const std::string& text) {
    // Stub: In production, integrate SymSpell or similar
    // For now, return input unchanged
    return text;
}

std::map<std::string, std::string> extract_invoice_fields(const std::string& ocr_text) {
    std::map<std::string, std::string> fields;
    // Invoice number (simple regex, e.g. INV12345)
    std::regex invnum_re(R"((INV\s*\d+))", std::regex::icase);
    std::smatch m;
    if (std::regex_search(ocr_text, m, invnum_re)) {
        fields["invoice_number"] = m.str(1);
    }
    // Date (simple regex for dd/mm/yyyy or yyyy-mm-dd)
    std::regex date_re(R"((\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2}))");
    if (std::regex_search(ocr_text, m, date_re)) {
        fields["date"] = m.str(1);
    }
    // Total (look for 'Total' followed by currency/number)
    std::regex total_re(R"(Total[^\d]*(\d+[.,]\d{2}))", std::regex::icase);
    if (std::regex_search(ocr_text, m, total_re)) {
        fields["total"] = m.str(1);
    }
    return fields;
}

void test_invoice_field_extraction() {
    std::string sample = R"(
        Invoice Number: INV12345
        Date: 2023-05-12
        Total: $1,234.56
    )";
    auto fields = extract_invoice_fields(sample);
    std::cout << "Extracted fields:\n";
    for (const auto& kv : fields) {
        std::cout << "  " << kv.first << ": " << kv.second << "\n";
    }
    // Simple asserts (manual)
    if (fields["invoice_number"] != "INV12345") std::cerr << "Invoice number extraction failed!\n";
    if (fields["date"] != "2023-05-12") std::cerr << "Date extraction failed!\n";
    if (fields["total"] != "1,234.56") std::cerr << "Total extraction failed!\n";
}

} // namespace postprocessing
} // namespace owlin

#ifdef OWLIN_POSTPROCESSING_TEST_MAIN
int main() {
    owlin::postprocessing::test_invoice_field_extraction();
    return 0;
}
#endif 