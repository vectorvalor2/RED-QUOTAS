#include "vulkan_engine.h"
#include <iostream>
#include <cstring>

namespace red_quotas {

VulkanEngine::VulkanEngine() {}

VulkanEngine::~VulkanEngine() {
    shutdown();
}

void VulkanEngine::initialize() {
    std::cout << "[Vulkan] Initializing Vulkan engine..." << std::endl;

    setupExtensions();
    setupLayers();

    // Create instance
    VkApplicationInfo app_info{};
    app_info.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app_info.pApplicationName = "RED-QUOTAS";
    app_info.applicationVersion = VK_MAKE_VERSION(1, 0, 0);
    app_info.pEngineName = "RED Engine";
    app_info.engineVersion = VK_MAKE_VERSION(1, 0, 0);
    app_info.apiVersion = VK_API_VERSION_1_3;

    VkInstanceCreateInfo create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    create_info.pApplicationInfo = &app_info;

    if (vkCreateInstance(&create_info, nullptr, &instance_) != VK_SUCCESS) {
        std::cerr << "[Vulkan] Failed to create instance!" << std::endl;
        return;
    }

    selectPhysicalDevice();
    createLogicalDevice();

    std::cout << "[Vulkan] Engine initialized successfully" << std::endl;
}

void VulkanEngine::shutdown() {
    if (device_) {
        vkDestroyDevice(device_, nullptr);
        device_ = VK_NULL_HANDLE;
    }

    if (instance_) {
        vkDestroyInstance(instance_, nullptr);
        instance_ = VK_NULL_HANDLE;
    }
}

bool VulkanEngine::isAvailable() const {
    return instance_ != VK_NULL_HANDLE && device_ != VK_NULL_HANDLE;
}

const char* VulkanEngine::getDeviceName() const {
    if (physical_device_ == VK_NULL_HANDLE) return "Unknown";

    VkPhysicalDeviceProperties props;
    vkGetPhysicalDeviceProperties(physical_device_, &props);
    return props.deviceName;
}

uint64_t VulkanEngine::getTotalMemory() const {
    if (physical_device_ == VK_NULL_HANDLE) return 0;

    VkPhysicalDeviceMemoryProperties mem_props;
    vkGetPhysicalDeviceMemoryProperties(physical_device_, &mem_props);

    uint64_t total = 0;
    for (uint32_t i = 0; i < mem_props.memoryHeapCount; ++i) {
        total += mem_props.memoryHeaps[i].size;
    }
    return total;
}

void VulkanEngine::setupExtensions() {
    // Extensions will be set up as needed
}

void VulkanEngine::setupLayers() {
    // Validation layers setup
}

void VulkanEngine::selectPhysicalDevice() {
    uint32_t device_count = 0;
    vkEnumeratePhysicalDevices(instance_, &device_count, nullptr);

    if (device_count == 0) {
        std::cerr << "[Vulkan] No Vulkan devices found!" << std::endl;
        return;
    }

    std::vector<VkPhysicalDevice> devices(device_count);
    vkEnumeratePhysicalDevices(instance_, &device_count, devices.data());

    // Select first device (typically discrete GPU)
    physical_device_ = devices[0];

    VkPhysicalDeviceProperties props;
    vkGetPhysicalDeviceProperties(physical_device_, &props);
    std::cout << "[Vulkan] Selected device: " << props.deviceName << std::endl;
}

void VulkanEngine::createLogicalDevice() {
    // Find compute queue family
    uint32_t queue_family_count = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical_device_,
                                             &queue_family_count, nullptr);

    std::vector<VkQueueFamilyProperties> queue_families(queue_family_count);
    vkGetPhysicalDeviceQueueFamilyProperties(physical_device_,
                                             &queue_family_count,
                                             queue_families.data());

    for (uint32_t i = 0; i < queue_family_count; ++i) {
        if (queue_families[i].queueFlags & VK_QUEUE_COMPUTE_BIT) {
            compute_family_index_ = i;
            break;
        }
    }

    float priority = 1.0f;
    VkDeviceQueueCreateInfo queue_create_info{};
    queue_create_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue_create_info.queueFamilyIndex = compute_family_index_;
    queue_create_info.queueCount = 1;
    queue_create_info.pQueuePriorities = &priority;

    VkDeviceCreateInfo device_create_info{};
    device_create_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    device_create_info.queueCreateInfoCount = 1;
    device_create_info.pQueueCreateInfos = &queue_create_info;

    if (vkCreateDevice(physical_device_, &device_create_info, nullptr,
                       &device_) != VK_SUCCESS) {
        std::cerr << "[Vulkan] Failed to create logical device!" << std::endl;
        return;
    }

    vkGetDeviceQueue(device_, compute_family_index_, 0, &compute_queue_);
}

} // namespace red_quotas
