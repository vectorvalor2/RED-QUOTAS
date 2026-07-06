#include "simd_processor.h"
#include <immintrin.h>
#include <cmath>
#include <algorithm>

namespace red_quotas {

SIMDProcessor::SIMDProcessor(uint32_t frame_width, uint32_t frame_height)
    : width_(frame_width), height_(frame_height) {
    temp_buffer_.resize(frame_width * frame_height * 4, 0.0f);
}

SIMDProcessor::~SIMDProcessor() {}

void SIMDProcessor::extractFrame(const uint8_t* input, uint32_t input_format,
                                 float* output, uint32_t output_size) {
    // Convert input format to normalized float32 RGBA
    uint32_t pixel_count = width_ * height_;

    #pragma omp parallel for simd collapse(2)
    for (uint32_t y = 0; y < height_; ++y) {
        for (uint32_t x = 0; x < width_; ++x) {
            uint32_t idx = (y * width_ + x) * 4;
            uint32_t in_idx = idx;

            // Normalize from 0-255 to 0.0-1.0
            output[idx + 0] = input[in_idx + 0] / 255.0f;  // R
            output[idx + 1] = input[in_idx + 1] / 255.0f;  // G
            output[idx + 2] = input[in_idx + 2] / 255.0f;  // B
            output[idx + 3] = input[in_idx + 3] / 255.0f;  // A
        }
    }
}

void SIMDProcessor::replicateEffects(float* frame, uint32_t frame_size,
                                    const std::vector<float>& effect_params) {
    // Apply effect parameters to frame using SIMD
    for (uint32_t i = 0; i < frame_size; i += 8) {
        __m256 v = _mm256_loadu_ps(&frame[i]);

        // Apply effect intensity from params
        if (!effect_params.empty()) {
            __m256 intensity = _mm256_set1_ps(effect_params[0]);
            v = _mm256_mul_ps(v, intensity);
        }

        _mm256_storeu_ps(&frame[i], v);
    }
}

float SIMDProcessor::computeFrameDifference(const float* frame1,
                                           const float* frame2,
                                           uint32_t frame_size) {
    float difference = 0.0f;
    uint32_t simd_iterations = frame_size / 8;

    __m256 sum = _mm256_set1_ps(0.0f);

    for (uint32_t i = 0; i < simd_iterations; ++i) {
        __m256 v1 = _mm256_loadu_ps(&frame1[i * 8]);
        __m256 v2 = _mm256_loadu_ps(&frame2[i * 8]);

        __m256 diff = _mm256_sub_ps(v1, v2);
        diff = _mm256_mul_ps(diff, diff);  // Square
        sum = _mm256_add_ps(sum, diff);
    }

    // Horizontal sum
    __m128 v128 = _mm256_castps256_ps128(sum);
    v128 = _mm_add_ps(v128, _mm_movehl_ps(v128, v128));
    v128 = _mm_add_ss(v128, _mm_shuffle_ps(v128, v128, _MM_SHUFFLE(1, 1, 1, 1)));
    difference = _mm_cvtss_f32(v128);

    // Handle remainder
    uint32_t remainder = frame_size - (simd_iterations * 8);
    for (uint32_t i = 0; i < remainder; ++i) {
        float d = frame1[simd_iterations * 8 + i] - frame2[simd_iterations * 8 + i];
        difference += d * d;
    }

    return std::sqrt(difference / frame_size);
}

void SIMDProcessor::convertRGBToYUV(const float* rgb, float* yuv,
                                   uint32_t pixel_count) {
    #pragma omp parallel for simd
    for (uint32_t i = 0; i < pixel_count; ++i) {
        float r = rgb[i * 3 + 0];
        float g = rgb[i * 3 + 1];
        float b = rgb[i * 3 + 2];

        yuv[i * 3 + 0] = 0.299f * r + 0.587f * g + 0.114f * b;        // Y
        yuv[i * 3 + 1] = -0.14713f * r - 0.28886f * g + 0.436f * b;    // U
        yuv[i * 3 + 2] = 0.615f * r - 0.51499f * g - 0.10001f * b;     // V
    }
}

void SIMDProcessor::convertYUVToRGB(const float* yuv, float* rgb,
                                   uint32_t pixel_count) {
    #pragma omp parallel for simd
    for (uint32_t i = 0; i < pixel_count; ++i) {
        float y = yuv[i * 3 + 0];
        float u = yuv[i * 3 + 1];
        float v = yuv[i * 3 + 2];

        rgb[i * 3 + 0] = y + 1.13983f * v;                       // R
        rgb[i * 3 + 1] = y - 0.39465f * u - 0.58060f * v;        // G
        rgb[i * 3 + 2] = y + 2.03211f * u;                       // B
    }
}

void SIMDProcessor::applyGaussianBlur(float* frame, uint32_t width,
                                     uint32_t height, float sigma,
                                     uint32_t kernel_size) {
    // Gaussian blur using separable kernels
    std::vector<float> kernel(kernel_size);
    float sum = 0.0f;

    int half = kernel_size / 2;
    for (int i = 0; i < (int)kernel_size; ++i) {
        int x = i - half;
        kernel[i] = std::exp(-(x * x) / (2.0f * sigma * sigma));
        sum += kernel[i];
    }

    // Normalize
    for (auto& k : kernel) k /= sum;

    // TODO: Apply separable convolution
}

void SIMDProcessor::computeOpticalFlow(const float* frame1, const float* frame2,
                                      uint32_t width, uint32_t height,
                                      float* flow_x, float* flow_y) {
    // Compute optical flow using Lucas-Kanade or similar
    // TODO: Implement optical flow computation
}

void SIMDProcessor::simd_memcpy_float(float* dst, const float* src,
                                      size_t count) {
    size_t simd_count = count / 8;
    for (size_t i = 0; i < simd_count; ++i) {
        __m256 v = _mm256_loadu_ps(&src[i * 8]);
        _mm256_storeu_ps(&dst[i * 8], v);
    }

    // Handle remainder
    for (size_t i = simd_count * 8; i < count; ++i) {
        dst[i] = src[i];
    }
}

void SIMDProcessor::simd_scale_float(float* dst, const float* src,
                                     float scale, size_t count) {
    __m256 scale_vec = _mm256_set1_ps(scale);
    size_t simd_count = count / 8;

    for (size_t i = 0; i < simd_count; ++i) {
        __m256 v = _mm256_loadu_ps(&src[i * 8]);
        v = _mm256_mul_ps(v, scale_vec);
        _mm256_storeu_ps(&dst[i * 8], v);
    }

    // Handle remainder
    for (size_t i = simd_count * 8; i < count; ++i) {
        dst[i] = src[i] * scale;
    }
}

} // namespace red_quotas
