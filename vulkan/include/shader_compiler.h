#pragma once

#include <vulkan/vulkan.h>
#include <vector>
#include <string>

namespace red_quotas {

class ShaderCompiler {
public:
    ShaderCompiler(VkDevice device);
    ~ShaderCompiler();

    // Compile GLSL compute shader to SPIR-V
    std::vector<uint32_t> compileGLSL(const std::string& glsl_source,
                                       const std::string& shader_name);

    // Create shader module from SPIR-V
    VkShaderModule createShaderModule(const std::vector<uint32_t>& spirv);

    // Predefined shader sources
    static std::string getExtractShader();
    static std::string getReplicantShader();
    static std::string getDeduplicateShader();
    static std::string getEffectsShader();

private:
    VkDevice device_;
};

} // namespace red_quotas
