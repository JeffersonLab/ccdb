"""The standard property names per owner type (docs/cli.md, "Properties"): the vocabulary `ccdb prop set` checks.

A name outside it is allowed: `prop set` warns, and `--free` silences the warning. An instance extends the vocabulary
with its own property `property_names`, a comma-separated list, so that names an experiment agreed on pass without
the flag. The HTTP API serves the vocabulary at /api/v1/properties/vocabulary; the table in docs/cli.md is generated
from STANDARD_NAMES by scripts/docs/vocabulary_table.py.
"""
from collections import OrderedDict

# The meaning of each name, shown in the docs table and served by the API
MEANINGS = OrderedDict([
    ("experiment", "the experiment the instance serves"),
    ("description", "what the object holds, in a sentence or two"),
    ("license", "the terms of use of the constants, an SPDX id such as CC-BY-4.0"),
    ("citation", "how to cite the constants"),
    ("contact", "who answers questions about the object"),
    ("url", "the published address of the instance's web GUI; data cards and tag exports link to it"),
    ("publisher", "the organization that publishes the constants, for the DataCite record of a tag export"),
    ("creator", "the creator named in the DataCite record of a tag export; the experiment's collaboration by default"),
    ("property_names", "names this instance adds to the vocabulary, comma-separated"),
    ("keywords", "words to find the object by, comma-separated"),
    ("source_url", "the code that produces the constants"),
    ("doc_url", "the documentation of the constants"),
    ("software", "the software release of the pass a tag names"),
    ("container", "the container image of the pass"),
    ("data", "the input data of the pass"),
    ("rucio_did", "the Rucio data identifier of the pass's output"),
    ("doi", "the DOI of the deposited export of the tag"),
])

_OBJECT_NAMES = ("description", "contact", "keywords", "source_url", "doc_url", "license", "citation")

STANDARD_NAMES = OrderedDict([
    ("instance", ("experiment", "description", "license", "citation", "contact", "url", "publisher", "creator",
                  "property_names")),
    ("directory", _OBJECT_NAMES),
    ("table", _OBJECT_NAMES),
    ("variation", _OBJECT_NAMES),
    ("tag", ("description", "software", "container", "data", "rucio_did", "doi", "citation")),
])


def instance_additions(provider):
    """The names of the instance property `property_names`, in its order"""
    prop = provider.get_property("instance", 0, "property_names")
    if prop is None:
        return []
    return [name.strip() for name in prop.value.split(",") if name.strip()]


def known_names(provider, owner_type):
    """Every name `prop set` accepts without a warning for this owner type"""
    return list(STANDARD_NAMES.get(owner_type, ())) + instance_additions(provider)


def is_known(provider, owner_type, name):
    return name in known_names(provider, owner_type)


def vocabulary(provider=None):
    """The vocabulary as plain data: per owner type its names, the meaning of every name, the instance's additions"""
    return {"owner_types": {owner: list(names) for owner, names in STANDARD_NAMES.items()},
            "meanings": dict(MEANINGS),
            "instance_additions": instance_additions(provider) if provider is not None else []}
