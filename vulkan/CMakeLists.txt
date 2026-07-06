cmake_minimum_required(VERSION 3.20)
project(RED_QUOTAS_VULKAN LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Vulkan
find_package(Vulkan REQUIRED)

# SIMD detection
if(MSVC)
    add_compile_options(/arch:AVX2)
else()
    add_compile_options(-march=native -mavx2 -mfma)
endif()

# Source files
set(SOURCES
    src/vulkan_engine.cpp
    src/simd_processor.cpp
    src/shader_compiler.cpp
    src/frame_pipeline.cpp
)

set(HEADERS
    include/vulkan_engine.h
    include/simd_processor.h
    include/shader_compiler.h
    include/frame_pipeline.h
    include/red_framework.h
)

# Create library
add_library(red_quotas_vulkan SHARED ${SOURCES})

target_include_directories(red_quotas_vulkan
    PUBLIC
        include
    PRIVATE
        src
)

target_link_libraries(red_quotas_vulkan
    PUBLIC
        Vulkan::Vulkan
)

# Testing
enable_testing()
add_subdirectory(tests)
