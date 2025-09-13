#include "segmentation_c_api.h"
#include "segmentation.h"
#include <cstring>
#include <vector>
#include <exception>

using namespace owlin::segmentation;

struct SegmenterImpl {
    Segmenter* segmenter;
    std::string last_error;
};

static thread_local std::string g_last_error;
static thread_local std::string g_last_timing;

extern "C" {

Segmenter* segmenter_create() {
    try {
        auto* impl = new SegmenterImpl;
        impl->segmenter = new Segmenter();
        impl->last_error.clear();
        return impl;
    } catch (const std::exception& ex) {
        g_last_error = ex.what();
        return nullptr;
    }
}

void segmenter_destroy(Segmenter* seg) {
    if (seg) {
        delete seg->segmenter;
        delete seg;
    }
}

int segment_lines(Segmenter* seg, const unsigned char* img, int width, int height, int channels, int** out_boxes, int* out_count) {
    if (!seg || !img || width <= 0 || height <= 0 || channels != 1 || !out_boxes || !out_count) {
        g_last_error = "Invalid arguments to segment_lines";
        if (out_boxes) *out_boxes = nullptr;
        if (out_count) *out_count = 0;
        return 1;
    }
    try {
        cv::Mat mat(height, width, CV_8UC1, const_cast<unsigned char*>(img));
        std::string err;
        auto boxes = seg->segmenter->segment_lines(mat, err);
        if (!err.empty()) {
            g_last_error = err;
            *out_boxes = nullptr;
            *out_count = 0;
            return 2;
        }
        *out_count = static_cast<int>(boxes.size());
        if (boxes.empty()) {
            *out_boxes = nullptr;
            return 0;
        }
        *out_boxes = (int*)malloc(sizeof(int) * 4 * boxes.size());
        for (size_t i = 0; i < boxes.size(); ++i) {
            (*out_boxes)[4 * i + 0] = boxes[i].x;
            (*out_boxes)[4 * i + 1] = boxes[i].y;
            (*out_boxes)[4 * i + 2] = boxes[i].w;
            (*out_boxes)[4 * i + 3] = boxes[i].h;
        }
        g_last_error.clear();
        return 0;
    } catch (const std::exception& ex) {
        g_last_error = ex.what();
        if (out_boxes) *out_boxes = nullptr;
        if (out_count) *out_count = 0;
        return 3;
    }
}

const char* segmenter_get_last_timing() {
    return g_last_timing.c_str();
}

void owlin_free(void* ptr) {
    if (ptr) free(ptr);
}

const char* owlin_get_last_error() {
    return g_last_error.c_str();
}

} // extern "C" 