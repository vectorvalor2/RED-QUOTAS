#pragma once

#include <vulkan/vulkan.h>
#include <vector>
#include <memory>
#include <cstdint>

namespace red_quotas {

struct FrameBuffer {
    VkBuffer buffer;
    VkDeviceMemory memory;
    uint32_t size;
};

class FramePipeline {
public:
    FramePipeline(VkDevice device, VkPhysicalDevice physical_device);
    ~FramePipeline();

    // Create frame buffers
    void allocateFrameBuffers(uint32_t frame_width, uint32_t frame_height,
                             uint32_t num_frames);

    // Pipeline stages
    void extractFrame(const uint8_t* input, uint32_t input_format);
    void replicateEffects(const std::vector<float>& effect_params);
    void deduplicateFrames();
    void applyEffects(const std::vector<float>& effect_chain);

    // Get processed frame
    const float* getOutputFrame() const;

private:
    VkDevice device_;
    VkPhysicalDevice physical_device_;

    std::vector<FrameBuffer> frame_buffers_;
    uint32_t current_frame_index_ = 0;
};

} // namespace red_quotas
