#include <cstdlib>
#include <iostream>

#include "CCDB/Helpers/EnvUtils.h"

bool ccdb::ParsePositiveUIntSetting(const std::string& text, unsigned int& value, unsigned int maxValue)
{
    if(text.empty() || text.size() > 10) return false;

    unsigned long long result = 0;
    for(char c: text) {
        if(c < '0' || c > '9') return false;
        result = result * 10 + static_cast<unsigned long long>(c - '0');
    }

    if(result == 0 || result > maxValue) return false;

    value = static_cast<unsigned int>(result);
    return true;
}


unsigned int ccdb::GetEnvPositiveUInt(const char* name, unsigned int defaultValue, unsigned int maxValue)
{
    const char* text = std::getenv(name);
    if(text == nullptr) return defaultValue;

    unsigned int value = defaultValue;
    if(!ParsePositiveUIntSetting(text, value, maxValue)) {
        std::cerr << "CCDB warning: environment variable " << name << "='" << text << "' is not a positive integer "
                  << "(max " << maxValue << "). Using the default value " << defaultValue << std::endl;
        return defaultValue;
    }
    return value;
}
