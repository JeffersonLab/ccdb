#ifndef CCDB_ENV_UTILS_H
#define CCDB_ENV_UTILS_H

#include <string>

namespace ccdb {

    /**
     * @brief Parses a strictly positive decimal integer setting such as a timeout
     *
     * Only digits are accepted (no sign, no spaces, no suffix); 0 and values
     * that do not fit into maxValue are rejected.
     *
     * @param [in]  text     - text to parse
     * @param [out] value    - parsed value, untouched if the text is invalid
     * @param [in]  maxValue - largest accepted value
     * @return true if the text is a valid value
     */
    bool ParsePositiveUIntSetting(const std::string& text, unsigned int& value, unsigned int maxValue);

    /**
     * @brief Reads a positive integer setting from an environment variable
     *
     * If the variable is not set, defaultValue is returned silently.
     * If it is set to an invalid value, a warning is printed to std::cerr and defaultValue is returned.
     */
    unsigned int GetEnvPositiveUInt(const char* name, unsigned int defaultValue, unsigned int maxValue);
}

#endif //CCDB_ENV_UTILS_H
