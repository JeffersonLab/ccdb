# String version. Used both for packaging (pyproject.toml dynamic version)
# and for internal code. Must be PEP 440 compliant so it is valid on PyPI.
version = "2.0.5"

# version as a tuple of ints, e.g. (2, 0, 5)
version_tuple = tuple(int(token) for token in version.split("."))

# individual components, kept for backwards compatibility
major, minor, patch = version_tuple
