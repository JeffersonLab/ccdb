// SPDX-License-Identifier: LGPL-3.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.
//
// SHA-256 (FIPS 180-4) for CCDB_service::GetResource, which verifies the files it fetches against the sha256
// column of a resources table. Its own small implementation, because the service depends on JANA2 and the
// ccdb library only (ccdb-2.5.md, D2).

#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

namespace ccdb_jana2 {

class Sha256 {
public:
    Sha256();

    void Update(const void* data, size_t size);

    /// Lower-case hex digest, the form CCDB stores; the object can't be updated afterwards
    std::string HexDigest();

    /// The digest of a whole file, read in blocks; throws std::runtime_error if the file can't be read
    static std::string OfFile(const std::string& path);

    static std::string OfString(const std::string& text);

private:
    void ProcessBlock(const uint8_t* block);

    uint32_t m_state[8];
    uint8_t m_block[64];
    size_t m_block_size = 0;     ///< bytes waiting in m_block
    uint64_t m_total_size = 0;   ///< bytes seen, for the length field of the padding
};

} // namespace ccdb_jana2
