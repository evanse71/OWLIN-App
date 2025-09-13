# Preprocessing module CMakeLists.txt
add_library(owlin_preprocessing STATIC
    preprocessing.cpp
    tesseract_preprocessing.cpp
)

target_link_libraries(owlin_preprocessing ${OpenCV_LIBS})

# Add Leptonica dependency for Tesseract preprocessing
find_package(PkgConfig REQUIRED)
pkg_check_modules(LEPT lept REQUIRED)
target_include_directories(owlin_preprocessing PUBLIC ${LEPT_INCLUDE_DIRS})
target_link_libraries(owlin_preprocessing ${LEPT_LIBRARIES})

# Add test executable
add_executable(test_preprocessing preprocessing.cpp)
target_link_libraries(test_preprocessing owlin_preprocessing ${OpenCV_LIBS} ${LEPT_LIBRARIES})
set_target_properties(test_preprocessing PROPERTIES COMPILE_DEFINITIONS OWLIN_PREPROCESSING_TEST_MAIN) 