"""The export of a tag (`ccdb export tag @NAME -o DIR`, docs/concepts/tags.md "Publishing a tag").

Writes three files:

    DIR/NAME.sqlite          the constants the tag gives for every run, as a CCDB database: every table, the tag's
                             variation and its parents, every assignment the tag sees for any run, the tag itself and
                             the properties of the instance, directories, tables, columns, those variations and the tag
    DIR/NAME.sha256          the SHA-256 of the file, in the format of sha256sum
    DIR/NAME.datacite.json   a DataCite 4.5 metadata record built from the instance and tag properties

The file opens with the Python and C++ libraries like any CCDB database; a request /path:run@NAME gives in the file
what it gives in the source. CCDB contacts no outside service: a person or a CI job uploads the files to a
repository (Zenodo, OSTI) and records the DOI it assigns with `ccdb prop set @NAME doi DOI`; the next export of
the same tag names that DOI as the previous version.
"""
import datetime
import json
import hashlib
import os
import warnings

from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import sessionmaker

from ccdb.model import INFINITE_RUN
from ccdb.provider import AlchemyProvider
from ccdb.snapshot import RowCopier, hide_password, open_engine, shallow_copy

DATACITE_SCHEMA = "http://datacite.org/schema/kernel-4"
SQLITE_MEDIA_TYPE = "application/vnd.sqlite3"


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def datacite_record(tag_name, tag_comment, snapshot_utc, instance, tag_properties, sha256, size, now_utc):
    """The DataCite 4.5 record (JSON attributes) of an exported tag.

    instance and tag_properties are {name: value}. The instance gives the creator and publisher (experiment,
    publisher), the contact person, the license and the landing URL; the tag gives the description, the software, container, data and
    rucio_did of the pass, and the DOI of the previous export. No DOI of its own: the repository assigns it."""
    experiment = instance.get("experiment", "")
    creator = instance.get("creator") or (experiment + " Collaboration" if experiment else "CCDB")
    record = {
        "schemaVersion": DATACITE_SCHEMA,
        "types": {"resourceTypeGeneral": "Dataset", "resourceType": "Calibration constants"},
        "titles": [{"title": "{0}calibration constants, tag {1}".format(experiment + " " if experiment else "", tag_name)}],
        "creators": [{"name": creator, "nameType": "Organizational"}],
        "publisher": {"name": instance.get("publisher") or experiment or "CCDB"},
        "publicationYear": str(now_utc.year),
        "version": tag_name,
        "subjects": [{"subject": "calibration constants"}, {"subject": "CCDB"}],
        "dates": [{"date": now_utc.strftime("%Y-%m-%d"), "dateType": "Created"},
                  {"date": snapshot_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), "dateType": "Other",
                   "dateInformation": "the moment the tag freezes: the newest constants created at or before it"}],
        "formats": [SQLITE_MEDIA_TYPE],
        "sizes": ["{0} bytes".format(size)],
        "alternateIdentifiers": [{"alternateIdentifier": sha256, "alternateIdentifierType": "SHA-256"}],
        "descriptions": [],
        "relatedIdentifiers": [],
    }
    abstract = tag_properties.get("description") or tag_comment
    if abstract:
        record["descriptions"].append({"description": abstract, "descriptionType": "Abstract"})
    technical = ["{0}: {1}".format(label, tag_properties[key]) for key, label in
                 (("software", "Software"), ("container", "Container"), ("data", "Data"), ("rucio_did", "Rucio DID"))
                 if tag_properties.get(key)]
    technical.append("A CCDB database (SQLite); a request /path:run@{0} gives the constants of the tag".format(tag_name))
    record["descriptions"].append({"description": ". ".join(technical), "descriptionType": "TechnicalInfo"})
    citation = tag_properties.get("citation") or instance.get("citation")
    if citation:
        record["descriptions"].append({"description": "Cite as: " + citation, "descriptionType": "Other"})
    if instance.get("contact"):
        record["contributors"] = [{"name": instance["contact"], "contributorType": "ContactPerson"}]
    if instance.get("license"):
        record["rightsList"] = [{"rights": instance["license"]}]
    if instance.get("url", "").startswith(("http://", "https://")):
        record["url"] = instance["url"]
    previous = tag_properties.get("doi", "")
    if previous:
        doi = previous.split("doi.org/", 1)[-1]
        record["relatedIdentifiers"].append({"relatedIdentifier": doi, "relatedIdentifierType": "DOI",
                                             "relationType": "IsNewVersionOf"})
    return record


def export_tag(source_url, tag_name, directory, now_utc=None):
    """Writes the three files of a tag export into `directory`; returns a report dict with their paths.

    Refuses to overwrite: a published export is a file other people may already hold."""
    # SQLite reflection reports column types like INTEGER(11) it cannot rebuild; the copy does not need them
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SAWarning)
        return _export_tag(source_url, tag_name, directory, now_utc)


def _export_tag(source_url, tag_name, directory, now_utc):
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None, microsecond=0)
    engine = open_engine(source_url)
    try:
        provider = AlchemyProvider()
        provider.attach(engine, sessionmaker(bind=engine)())
        tag = provider.get_tag(tag_name)
        chain = provider.get_variation_tree_up(provider.get_tag_variation(tag))
        tag_id, snapshot, comment = tag.id, tag.snapshot_time, tag.comment or ""
        instance = {prop.name: prop.value for prop in provider.get_properties("instance", 0)}
        tag_properties = {prop.name: prop.value for prop in provider.get_properties("tag", tag_id)}
        provider.session.close()
    finally:
        engine.dispose()

    os.makedirs(directory, exist_ok=True)
    paths = {kind: os.path.join(directory, tag_name + suffix)
             for kind, suffix in (("sqlite", ".sqlite"), ("sha256", ".sha256"), ("datacite", ".datacite.json"))}
    for path in paths.values():
        if os.path.exists(path):
            raise FileExistsError("{0} exists. An export is not overwritten; remove it or choose another directory".format(path))

    partial = paths["sqlite"] + ".part"
    if os.path.exists(partial):
        os.remove(partial)
    moment = snapshot.replace(tzinfo=datetime.timezone.utc)
    report = shallow_copy(source_url, "sqlite:///" + partial, 0, INFINITE_RUN, [chain[0].name], moment, tag=tag_name)

    # The descriptions of what the file holds: they are part of the record a reader of the file needs
    source, target = open_engine(source_url), open_engine("sqlite:///" + partial)
    try:
        copier = RowCopier(source, target)
        report["properties"] = copier.copy(
            "properties",
            "ownerType IN ('instance', 'directory', 'table', 'column') OR (ownerType = 'tag' AND ownerId = :tag_id) "
            "OR (ownerType = 'variation' AND ownerId IN :variation_ids)",
            {"tag_id": tag_id, "variation_ids": [variation.id for variation in chain]})
    finally:
        source.dispose()
        target.dispose()
    os.replace(partial, paths["sqlite"])

    sha256 = file_sha256(paths["sqlite"])
    size = os.path.getsize(paths["sqlite"])
    with open(paths["sha256"], "w", encoding="utf-8") as file:
        file.write("{0}  {1}\n".format(sha256, os.path.basename(paths["sqlite"])))
    record = datacite_record(tag_name, comment, snapshot, instance, tag_properties, sha256, size, now_utc)
    with open(paths["datacite"], "w", encoding="utf-8") as file:
        json.dump(record, file, indent=1, ensure_ascii=False)
        file.write("\n")

    report.update(paths=paths, sha256=sha256, bytes=size, source=hide_password(source_url))
    return report
