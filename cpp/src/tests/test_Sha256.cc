// ccdb::Sha256, which checks the run bundles the HTTP provider downloads: the FIPS 180-4 example messages, and a
// message fed in pieces gives the digest of the whole.
#include "tests/catch.hpp"

#include "CCDB/Helpers/Sha256.h"

#include <string>

using namespace ccdb;

TEST_CASE("Sha256/known digests", "[Sha256]")
{
    REQUIRE(Sha256::Of("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    REQUIRE(Sha256::Of("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    REQUIRE(Sha256::Of("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") ==
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1");
    REQUIRE(Sha256::Of(std::string(1000000, 'a')) == "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
}

TEST_CASE("Sha256/pieces", "[Sha256]")
{
    // every split of a message that crosses the 64-byte blocks and the 56-byte padding boundary
    std::string message;
    for (int i = 0; i < 130; i++) message += static_cast<char>(i * 7);
    std::string whole = Sha256::Of(message);
    for (size_t split = 0; split <= message.size(); split++) {
        Sha256 hash;
        hash.Update(message.data(), split);
        hash.Update(message.data() + split, message.size() - split);
        REQUIRE(hash.HexDigest() == whole);
    }
    for (size_t size = 50; size < 70; size++) {
        Sha256 bytewise;
        for (size_t i = 0; i < size; i++) bytewise.Update(message.data() + i, 1);
        REQUIRE(bytewise.HexDigest() == Sha256::Of(message.substr(0, size)));
    }
}
