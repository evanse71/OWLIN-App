file(GLOB API_SRC *.cpp)
add_library(api_obj OBJECT ${API_SRC})
target_link_libraries(api_obj ${OpenCV_LIBS} ${LEPT_LIBRARIES})
target_include_directories(api_obj PUBLIC ${CMAKE_SOURCE_DIR}/include) 