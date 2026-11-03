import re

# String version. Used both for packaging (pyproject.toml dynamic version)
# and for internal code. Must be PEP 440 compliant so it is valid on PyPI.
version = "2.5.0"


def parse_version(text):
    """(major, minor, patch) of a PEP 440 version text such as '2.5.0', '2.5.0.dev0', '2.5.0rc1' or '2.4.1.post2'.

    The pre-release, post-release and development suffixes are accepted and dropped: the tuple names the release
    the text belongs to, so '2.5.0.dev0' gives (2, 5, 0).
    """
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:(?:a|b|rc)\d+)?(?:\.post\d+)?(?:\.dev\d+)?$", text.strip())
    if not match:
        raise ValueError(f"'{text}' is not a version of the form MAJOR.MINOR.PATCH with an optional "
                         f".devN, aN, bN, rcN or .postN suffix")
    return tuple(int(token) for token in match.groups())


# version as a tuple of ints, e.g. (2, 5, 0)
version_tuple = parse_version(version)

# individual components, kept for backwards compatibility
major, minor, patch = version_tuple
