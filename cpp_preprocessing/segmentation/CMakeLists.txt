cmake_minimum_required(VERSION 3.10)
project(owlin_segmentation)

find_package(OpenCV REQUIRED)

add_library(owlin_segmentation
    segmentation.cpp
    segmentation.h
    segmentation_c_api.cpp
    segmentation_c_api.h
)

target_include_directories(owlin_segmentation PUBLIC ${OpenCV_INCLUDE_DIRS} .)
target_link_libraries(owlin_segmentation PUBLIC ${OpenCV_LIBS})

# CLI test
add_executable(line_segmentation_cli line_segmentation.cpp)
target_compile_definitions(line_segmentation_cli PRIVATE OWLIN_LINE_SEGMENTATION_CLI)
target_link_libraries(line_segmentation_cli PRIVATE line_segmentation preprocessing opencv_core opencv_imgproc opencv_highgui opencv_imgcodecs) 