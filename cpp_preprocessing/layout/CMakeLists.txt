file(GLOB LAYOUT_SRC *.cpp)
add_library(layout_obj OBJECT ${LAYOUT_SRC})
target_link_libraries(layout_obj ${OpenCV_LIBS} ${LEPT_LIBRARIES})
target_include_directories(layout_obj PUBLIC ${CMAKE_SOURCE_DIR}/include) 