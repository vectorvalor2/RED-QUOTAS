#pragma once

#include <vulkan/vulkan.h>
#include <vector>
#include <memory>
#include <cstdint>

namespace red_quotas {

class VulkanEngine {
public:
    VulkanEngine();
    ~VulkanEngine();

    // Initialize Vulkan instance, device, and command queue
    void initialize();
    void shutdown();

    // Check Vulkan support and device capabilities
    bool isAvailable() const;
    const char* getDeviceName() const;
    uint64_t getTotalMemory() const;

    // Get Vulkan handles for external use
    VkInstance getInstance() const { return instance_; }
    VkDevice getDevice() const { return device_; }
    VkPhysicalDevice getPhysicalDevice() const { return physical_device_; }
    VkQueue getComputeQueue() const { return compute_queue_; }

private:
    void setupLayers();
    void setupExtensions();
    void selectPhysicalDevice();
    void createLogicalDevice();

    VkInstance instance_ = VK_NULL_HANDLE;
    VkPhysicalDevice physical_device_ = VK_NULL_HANDLE;
    VkDevice device_ = VK_NULL_HANDLE;
    VkQueue compute_queue_ = VK_NULL_HANDLE;
    uint32_t compute_family_index_ = 0;
};

} // namespace red_quotas
