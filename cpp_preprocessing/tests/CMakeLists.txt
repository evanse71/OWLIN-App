# Add Catch2-based test executables for recognition and segmentation
find_package(Catch2 REQUIRED)

add_executable(test_recognition test_recognition.cpp)
target_link_libraries(test_recognition PRIVATE owlin_recognition Catch2::Catch2WithMain OpenCV::opencv_core OpenCV::opencv_imgcodecs)

add_executable(test_segmentation test_segmentation.cpp)
target_link_libraries(test_segmentation PRIVATE owlin_segmentation Catch2::Catch2WithMain OpenCV::opencv_core OpenCV::opencv_imgcodecs)

add_executable(test_pipeline test_pipeline.cpp)
target_link_libraries(test_pipeline PRIVATE owlin_recognition owlin_segmentation Catch2::Catch2WithMain OpenCV::opencv_core OpenCV::opencv_imgcodecs) 