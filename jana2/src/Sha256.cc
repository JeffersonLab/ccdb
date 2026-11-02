// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.

#include "Sha256.h"

#include <algorithm>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <vector>

namespace ccdb_jana2 {

namespace {
    const uint32_t ROUND_CONSTANTS[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

    inline uint32_t RotateRight(uint32_t value, int bits) { return (value >> bits) | (value << (32 - bits)); }
}


Sha256::Sha256()
    : m_state{0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19} {}


void Sha256::ProcessBlock(const uint8_t* block) {
    uint32_t schedule[64];
    for (int word_i = 0; word_i < 16; word_i++) {
        schedule[word_i] = (uint32_t(block[word_i * 4]) << 24) | (uint32_t(block[word_i * 4 + 1]) << 16) |
                           (uint32_t(block[word_i * 4 + 2]) << 8) | uint32_t(block[word_i * 4 + 3]);
    }
    for (int word_i = 16; word_i < 64; word_i++) {
        uint32_t s0 = RotateRight(schedule[word_i - 15], 7) ^ RotateRight(schedule[word_i - 15], 18) ^ (schedule[word_i - 15] >> 3);
        uint32_t s1 = RotateRight(schedule[word_i - 2], 17) ^ RotateRight(schedule[word_i - 2], 19) ^ (schedule[word_i - 2] >> 10);
        schedule[word_i] = schedule[word_i - 16] + s0 + schedule[word_i - 7] + s1;
    }

    uint32_t a = m_state[0], b = m_state[1], c = m_state[2], d = m_state[3];
    uint32_t e = m_state[4], f = m_state[5], g = m_state[6], h = m_state[7];
    for (int round_i = 0; round_i < 64; round_i++) {
        uint32_t sum1 = RotateRight(e, 6) ^ RotateRight(e, 11) ^ RotateRight(e, 25);
        uint32_t choice = (e & f) ^ (~e & g);
        uint32_t temp1 = h + sum1 + choice + ROUND_CONSTANTS[round_i] + schedule[round_i];
        uint32_t sum0 = RotateRight(a, 2) ^ RotateRight(a, 13) ^ RotateRight(a, 22);
        uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = sum0 + majority;
        h = g; g = f; f = e; e = d + temp1;
        d = c; c = b; b = a; a = temp1 + temp2;
    }
    m_state[0] += a; m_state[1] += b; m_state[2] += c; m_state[3] += d;
    m_state[4] += e; m_state[5] += f; m_state[6] += g; m_state[7] += h;
}


void Sha256::Update(const void* data, size_t size) {
    const uint8_t* bytes = static_cast<const uint8_t*>(data);
    m_total_size += size;
    while (size > 0) {
        size_t take = std::min(size, sizeof(m_block) - m_block_size);
        std::memcpy(m_block + m_block_size, bytes, take);
        m_block_size += take;
        bytes += take;
        size -= take;
        if (m_block_size == sizeof(m_block)) {
            ProcessBlock(m_block);
            m_block_size = 0;
        }
    }
}


std::string Sha256::HexDigest() {
    // Padding: 0x80, zeros up to 56 bytes of the last block, then the message length in bits, big endian
    uint64_t total_bits = m_total_size * 8;
    uint8_t padding[64] = {0x80};
    size_t padding_size = (m_block_size < 56) ? 56 - m_block_size : 120 - m_block_size;
    Update(padding, padding_size);
    uint8_t length[8];
    for (int byte_i = 0; byte_i < 8; byte_i++) length[byte_i] = uint8_t(total_bits >> (56 - 8 * byte_i));
    Update(length, sizeof(length));

    static const char* HEX = "0123456789abcdef";
    std::string digest;
    for (uint32_t word: m_state) {
        for (int shift = 28; shift >= 0; shift -= 4) digest += HEX[(word >> shift) & 0xf];
    }
    return digest;
}


std::string Sha256::OfFile(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("can't open '" + path + "' to compute its SHA-256");
    Sha256 hash;
    std::vector<char> buffer(1 << 20);
    while (file.read(buffer.data(), buffer.size()) || file.gcount() > 0) {
        hash.Update(buffer.data(), static_cast<size_t>(file.gcount()));
    }
    if (file.bad()) throw std::runtime_error("error reading '" + path + "' to compute its SHA-256");
    return hash.HexDigest();
}


std::string Sha256::OfString(const std::string& text) {
    Sha256 hash;
    hash.Update(text.data(), text.size());
    return hash.HexDigest();
}

} // namespace ccdb_jana2
