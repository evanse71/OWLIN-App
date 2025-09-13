#pragma once

#ifdef __cplusplus
extern "C" {
#endif

typedef struct SegmenterImpl Segmenter;

Segmenter* segmenter_create();
void segmenter_destroy(Segmenter* seg);
int segment_lines(Segmenter* seg, const unsigned char* img, int width, int height, int channels, int** out_boxes, int* out_count);
void owlin_free(void* ptr);
const char* owlin_get_last_error();

#ifdef __cplusplus
}
#endif 