file(GLOB POSTPROCESSING_SRC *.cpp)
add_library(postprocessing_obj OBJECT ${POSTPROCESSING_SRC})
target_link_libraries(postprocessing_obj ${OpenCV_LIBS} ${LEPT_LIBRARIES})
target_include_directories(postprocessing_obj PUBLIC ${CMAKE_SOURCE_DIR}/include) 