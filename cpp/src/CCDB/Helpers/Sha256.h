#ifndef _Sha256_
#define _Sha256_

#include <stddef.h>
#include <stdint.h>
#include <string>

namespace ccdb
{
/** @brief SHA-256 (FIPS 180-4), fed in pieces, for the run bundles the HTTP provider downloads.
 *
 * The API sends the SHA-256 of a bundle in X-CCDB-SHA256; the provider hashes the bytes as they arrive
 * and keeps the file only when the two agree. The library has no other hashing dependency.
 */
class Sha256
{
public:
    Sha256();

    /** @brief Adds bytes to the message */
    void Update(const void* data, size_t size);

    /** @brief The digest of the bytes added so far as 64 lowercase hexadecimal digits; ends the message */
    std::string HexDigest();

    /** @brief The digest of one string */
    static std::string Of(const std::string& data);

private:
    void Block(const uint8_t* block);

    uint32_t mState[8];
    uint8_t mBuffer[64];
    size_t mBuffered;
    uint64_t mLength;           ///< bytes added
    bool mFinished;
};
}

#endif // _Sha256_
