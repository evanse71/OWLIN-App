cmake_minimum_required(VERSION 3.10)
project(OwlinOCR LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -Wall -Wextra")

# Find dependencies
find_package(OpenCV REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(LEPT lept REQUIRED)
find_package(Tesseract REQUIRED)

include_directories(
    ${OpenCV_INCLUDE_DIRS}
    ${LEPT_INCLUDE_DIRS}
    ${Tesseract_INCLUDE_DIRS}
    ${CMAKE_SOURCE_DIR}/include
)

# Add subdirectories for each module
add_subdirectory(preprocessing)
add_subdirectory(layout)
add_subdirectory(recognition)
add_subdirectory(postprocessing)
add_subdirectory(api)
add_subdirectory(tests)
add_subdirectory(segmentation)

# Gather all module sources
file(GLOB_RECURSE OWLIN_OCR_SOURCES
    preprocessing/*.cpp
    layout/*.cpp
    recognition/*.cpp
    postprocessing/*.cpp
    api/*.cpp
    segmentation/*.cpp
)

# Main shared/static library for Python/Streamlit integration
add_library(owlin_ocr SHARED ${OWLIN_OCR_SOURCES})
target_link_libraries(owlin_ocr 
    ${OpenCV_LIBS} 
    ${LEPT_LIBRARIES} 
    ${Tesseract_LIBRARIES}
    owlin_preprocessing
)
target_include_directories(owlin_ocr PUBLIC ${CMAKE_SOURCE_DIR}/include)

# Export symbols for Windows DLLs
if(WIN32)
    set_target_properties(owlin_ocr PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

# Add test targets to 'test' and 'all' build targets
enable_testing()
add_test(NAME test_recognition COMMAND test_recognition)
add_test(NAME test_segmentation COMMAND test_segmentation)
add_test(NAME test_pipeline COMMAND test_pipeline)
add_test(NAME test_tesseract_preprocessing COMMAND test_tesseract_preprocessing)

# Add Catch2 test for Tesseract preprocessing
find_package(Catch2 REQUIRED)
target_link_libraries(test_tesseract_preprocessing Catch2::Catch2)

# Print configuration summary
message(STATUS "Owlin OCR Configuration:")
message(STATUS "  OpenCV: ${OpenCV_VERSION}")
message(STATUS "  Leptonica: ${LEPT_VERSION}")
message(STATUS "  Tesseract: ${Tesseract_VERSION}")
message(STATUS "  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Build Type: ${CMAKE_BUILD_TYPE}") 