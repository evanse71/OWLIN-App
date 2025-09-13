cmake_minimum_required(VERSION 3.10)
project(owlin_recognition)

find_package(OpenCV REQUIRED)
find_package(Tesseract REQUIRED)

add_library(owlin_recognition
    recognition.cpp
    recognition.h
    recognition_c_api.cpp
    recognition_c_api.h
)

target_include_directories(owlin_recognition PUBLIC ${OpenCV_INCLUDE_DIRS} ${Tesseract_INCLUDE_DIRS} .)
target_link_libraries(owlin_recognition PUBLIC ${OpenCV_LIBS} ${Tesseract_LIBRARIES})

# CLI test
add_executable(recognition_cli recognition.cpp)
target_compile_definitions(recognition_cli PRIVATE OWLIN_OCR_RECOGNITION_CLI)
target_link_libraries(recognition_cli PRIVATE recognition opencv_core opencv_imgproc opencv_highgui opencv_imgcodecs) 