#pragma once

#include <cstdint>
#include <vector>
#include <string>

namespace red_quotas {

/*
 * RED Framework: Replicant, Extract, Deduplicate
 *
 * EXTRACT: Parse diverse input formats (video, images, 3D, point clouds, audio)
 *          Convert to normalized frame buffers
 *
 * REPLICANT: Use SIMD/GPU to parallelize frame transformations
 *            Apply effects, filters, and compositing
 *
 * DEDUPLICATE: Intelligent caching and frame delta compression
 *              Reduce memory/bandwidth using frame difference detection
 */

enum class InputFormat : uint32_t {
    VIDEO_H264 = 0,
    VIDEO_HEVC = 1,
    VIDEO_VP9 = 2,
    IMAGE_PNG = 3,
    IMAGE_JPEG = 4,
    IMAGE_WEBP = 5,
    MODEL_OBJ = 6,
    MODEL_GLTF = 7,
    POINTCLOUD_PLY = 8,
    AUDIO_WAV = 9,
    AUDIO_MP3 = 10,
};

enum class EffectType : uint32_t {
    MOTION_BLUR = 0,
    NEON_GLOW = 1,
    TIME_WARP = 2,
    CHROMATIC_ABERRATION = 3,
    PARTICLE_DISTORTION = 4,
    GLITCH = 5,
    COLOR_GRADING = 6,
    BLOOM = 7,
};

struct ProcessingParams {
    float duration_seconds = 5.0f;
    uint32_t output_width = 1920;
    uint32_t output_height = 1080;
    uint32_t fps = 60;
    std::vector<EffectType> effects;
    std::vector<float> effect_strengths;
};

} // namespace red_quotas
