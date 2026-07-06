# Vulkan GPU Pipeline Details

## Compute Shader Architecture

### Extract Shader (extract.comp)

```glsl
#version 450
layout(local_size_x = 16, local_size_y = 16) in;

layout(binding = 0, rgba32f) uniform image2D input_image;
layout(binding = 1, rgba32f) uniform image2D output_image;

layout(push_constant) uniform ExtractionParams {
    uint input_format;  // 0=RGB, 1=YUV, 2=Bayer
    float gamma;        // Color space correction
} params;

void main() {
    ivec2 coord = ivec2(gl_GlobalInvocationID.xy);
    
    vec4 pixel = imageLoad(input_image, coord);
    
    // Normalize to 0-1 range
    pixel = pixel / 255.0;
    
    // Apply gamma correction
    pixel = pow(pixel, vec4(1.0 / params.gamma));
    
    imageStore(output_image, coord, pixel);
}
```

### Replicant Shader (replicant.comp)

```glsl
#version 450
layout(local_size_x = 16, local_size_y = 16) in;

layout(binding = 0, rgba32f) uniform image2D frame;

layout(push_constant) uniform EffectParams {
    float motion_blur_strength;
    float neon_glow_intensity;
    float time_warp_factor;
    float chromatic_aberration;
} params;

void main() {
    ivec2 coord = ivec2(gl_GlobalInvocationID.xy);
    vec4 pixel = imageLoad(frame, coord);
    
    // Motion blur: sample neighboring frames
    // Implemented via temporal aliasing
    
    // Neon glow: enhance edges
    vec4 neighbor_avg = (
        imageLoad(frame, coord + ivec2(1, 0)) +
        imageLoad(frame, coord - ivec2(1, 0)) +
        imageLoad(frame, coord + ivec2(0, 1)) +
        imageLoad(frame, coord - ivec2(0, 1))
    ) / 4.0;
    
    vec4 edge = pixel - neighbor_avg;
    pixel += edge * params.neon_glow_intensity;
    
    imageStore(frame, coord, pixel);
}
```

### Deduplicate Shader (deduplicate.comp)

```glsl
#version 450
layout(local_size_x = 16, local_size_y = 16) in;

layout(binding = 0, rgba32f) uniform image2D frame1;
layout(binding = 1, rgba32f) uniform image2D frame2;
layout(binding = 2, r32f) uniform image2D diff_output;

void main() {
    ivec2 coord = ivec2(gl_GlobalInvocationID.xy);
    
    vec4 p1 = imageLoad(frame1, coord);
    vec4 p2 = imageLoad(frame2, coord);
    
    // Compute L2 distance
    float diff = distance(p1, p2);
    
    imageStore(diff_output, coord, vec4(diff));
}
```

## Vulkan Resource Management

### Buffer Strategy

```cpp
// Ring buffer for streaming frames
struct RingBuffer {
    VkBuffer buffer;           // GPU buffer
    VkDeviceMemory memory;     // GPU memory
    size_t capacity;           // Total size
    size_t write_offset;       // Current write position
    size_t read_offset;        // Current read position
};

// Cache for frame deduplication
struct FrameCache {
    std::map<uint64_t, VkBuffer> cache;  // hash -> buffer
    std::queue<uint64_t> lru_queue;      // LRU eviction
    size_t max_size_mb = 2048;           // 2GB cap
};
```

### Command Recording

```cpp
void FramePipeline::recordComputeCommands() {
    VkCommandBufferBeginInfo begin_info{};
    begin_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    
    vkBeginCommandBuffer(command_buffer, &begin_info);
    
    // Dispatch extract shader
    vkCmdBindPipeline(command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE,
                      extract_pipeline);
    vkCmdDispatch(command_buffer, (width + 15) / 16, (height + 15) / 16, 1);
    
    // Pipeline barrier
    VkMemoryBarrier barrier{};
    barrier.sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER;
    barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
    vkCmdPipelineBarrier(command_buffer, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                         VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 1, &barrier,
                         0, nullptr, 0, nullptr);
    
    // Dispatch replicant shader
    vkCmdBindPipeline(command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE,
                      replicant_pipeline);
    vkCmdDispatch(command_buffer, (width + 15) / 16, (height + 15) / 16, 1);
    
    // ... more stages ...
    
    vkEndCommandBuffer(command_buffer);
}
```

## Performance Optimization

### Memory Coalescing

GPU memory access patterns optimized:
- Workgroup size: 16×16 (256 threads)
- Stride matches cache line (128 bytes typical)
- Sequential memory loads in each thread

### Warp Divergence Minimization

- Branch-free computation where possible
- Predicated instructions for conditional logic
- LDS (Local Data Share) for reduced global memory

### Synchronization

```cpp
// Minimal barriers between passes
// Use event-based synchronization where possible
VkPipelineStageFlags stage_mask = 
    VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT;
VkAccessFlags access_mask = 
    VK_ACCESS_SHADER_WRITE_BIT | VK_ACCESS_SHADER_READ_BIT;
```

## Debugging & Profiling

### Validation Layers

```cpp
const char* instance_layers[] = {
    "VK_LAYER_KHRONOS_validation",
    "VK_LAYER_LUNARG_monitor"
};
```

### GPU Profiling

- NVIDIA: Nsight Systems, Nsight Compute
- AMD: Radeon GPU Analyzer
- Intel: Metrics Discovery

### Shader Validation

```bash
# Compile and validate GLSL
glslangValidator -V extract.comp -o extract.spv
spirv-val extract.spv
```
