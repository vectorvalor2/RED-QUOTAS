#pragma once

#include <cstdint>
#include <vector>
#include <memory>

namespace red_quotas {

// SIMD processor for parallel frame operations
class SIMDProcessor {
public:
    SIMDProcessor(uint32_t frame_width, uint32_t frame_height);
    ~SIMDProcessor();

    // Extract: Convert input format to normalized RGBA float32
    void extractFrame(const uint8_t* input, uint32_t input_format,
                      float* output, uint32_t output_size);

    // Replicant: Apply effects with SIMD parallelization
    void replicateEffects(float* frame, uint32_t frame_size,
                         const std::vector<float>& effect_params);

    // Deduplicate: Detect frame differences
    float computeFrameDifference(const float* frame1, const float* frame2,
                                uint32_t frame_size);

    // Color space conversions
    void convertRGBToYUV(const float* rgb, float* yuv, uint32_t pixel_count);
    void convertYUVToRGB(const float* yuv, float* rgb, uint32_t pixel_count);

    // Blur and convolution kernels
    void applyGaussianBlur(float* frame, uint32_t width, uint32_t height,
                          float sigma, uint32_t kernel_size);

    // Motion detection
    void computeOpticalFlow(const float* frame1, const float* frame2,
                           uint32_t width, uint32_t height,
                           float* flow_x, float* flow_y);

private:
    uint32_t width_;
    uint32_t height_;
    std::vector<float> temp_buffer_;

    // SIMD helper functions
    void simd_memcpy_float(float* dst, const float* src, size_t count);
    void simd_scale_float(float* dst, const float* src, float scale, size_t count);
};

} // namespace red_quotas
