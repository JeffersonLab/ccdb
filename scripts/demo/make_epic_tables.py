#!/usr/bin/env python3
"""ePIC-shaped demo tables: the calibration constants EICrecon v1.42.0 reads today, as CCDB tables (docs/get-started/demo.md).

    python scripts/demo/make_epic_tables.py sqlite:///epic_demo.sqlite
    python scripts/demo/make_epic_tables.py mysql://ccdb_user@127.0.0.1/ccdb_demo      (the database is re-initialized)

The names, shapes and values come from the EICrecon source at tag v1.42.0 (src/detectors/*/ plugin files and the
algorithm config structs); each table's `source_url` property names its file. Two run periods (runs 1-999 and
1000-1999) and two variations (default and mc, a child of default) show how constants change with the run and with
the variation; one tag, campaign_demo, freezes the state before a late correction. Every time and value is fixed, so
two builds of the database hold the same rows, as the unit test checks (python/tests/unit_test_demo_tables.py).

The demo adds one change per period that EICrecon does not have: the gains and sampling fractions of the second
period are 1 % higher, so a job that crosses run 1000 shows the switch.
"""
import argparse
import contextlib
import hashlib
import io
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EICRECON = "https://github.com/eic/EICrecon/blob/v1.42.0/"
START = datetime(2026, 1, 15, 9, 0, 0, tzinfo=timezone.utc)     # the first assignment; the rest follow by the minute
PERIODS = [(1, 999), (1000, 1999)]
TAG_TIME = datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)  # after the period assignments, before the late correction
RESOURCE_PATH = "/cvmfs/epic.example.org/calibrations/onnx/EcalEndcapN_pi_rejection.onnx"
RESOURCE_BYTES = b"demo stand-in for calibrations/onnx/EcalEndcapN_pi_rejection.onnx\n"

# (path, comment, source file, columns [(name, type, units)], rows of the first period, scale of the second period)
# `scaled` names the columns that change by +1 % in the second period.
TABLES = [
    ("/epic/EcalEndcapN/adc_calib", "EEEMCal digitization and reconstruction constants", "src/detectors/EEMC/EEMC.cc",
     [("capADC", "int", "counts"), ("dyRangeADC", "double", "GeV"), ("pedMeanADC", "int", "ADC"), ("pedSigmaADC", "double", "ADC"),
      ("resolutionTDC", "double", "ps"), ("thresholdValue", "double", "ADC"), ("sampFrac", "double", ""),
      ("lightYield", "double", "pe/MeV"), ("photonDetectionEfficiency", "double", "")],
     [[16384, 20.0, 20, 1.0, 10.0, 4.0, 0.96, 72.0, 0.0504]], ["sampFrac"]),
    ("/epic/EcalBarrel/adc_calib", "Barrel ECal (Pb/ScFi and AstroPix imaging layers) ADC constants", "src/detectors/BEMC/BEMC.cc",
     [("subsystem", "string", ""), ("capADC", "int", "counts"), ("dyRangeADC", "double", "MeV"), ("pedMeanADC", "int", "ADC"),
      ("pedSigmaADC", "double", "ADC"), ("resolutionTDC", "double", "ns"), ("thresholdValue", "double", "ADC"), ("sampFrac", "double", "")],
     [["ScFi", 16384, 1500.0, 100, 1.0, 0.010, 5.0, 0.09285755], ["Imaging", 8192, 3.0, 14, 5.0, 3.25, 41.0, 0.00429453]], ["sampFrac"]),
    ("/epic/EcalBarrel/scfi_attenuation", "Barrel ECal fibre light attenuation per readout end", "src/detectors/BEMC/BEMC.cc",
     [("end", "string", ""), ("referencePosition", "string", ""), ("attA", "double", ""), ("attL1", "double", "mm"),
      ("attL2", "double", "mm"), ("inversePropagationSpeed", "double", "ns/mm"), ("fixedTimeDelay", "double", "ns"), ("timeWindow", "double", "ns")],
     [["P", "EcalBarrel_LightGuide_PositivePosZ", 0.416212, 747.39875, 7521.88383, 0.00625, 2.0, 100.0],
      ["N", "EcalBarrel_LightGuide_NegativePosZ", 0.416212, 747.39875, 7521.88383, 0.00625, 2.0, 100.0]], []),
    ("/epic/EcalEndcapP/adc_calib", "Forward ECal ADC constants and energy resolution", "src/detectors/FEMC/FEMC.cc",
     [("capADC", "int", "counts"), ("dyRangeADC", "double", "GeV"), ("pedMeanADC", "int", "ADC"), ("pedSigmaADC", "double", "ADC"),
      ("resolutionTDC", "double", "ps"), ("capTime", "double", "ns"), ("thresholdValue", "double", "ADC"), ("sampFrac", "double", ""),
      ("eResStoch", "double", "sqrt(GeV)"), ("eResConst", "double", ""), ("nPhotonPerGeV", "double", ""), ("photonCollectionEff", "double", "")],
     [[16384, 100.0, 200, 2.4576, 10.0, 100.0, 3.0, 0.029043, 0.11333, 0.03, 1500.0, 0.285]], ["sampFrac"]),
    ("/epic/HCal/adc_calib", "Hadron calorimeters ADC constants, one row per detector",
     "src/detectors/BHCAL/BHCAL.cc, src/detectors/EHCAL/EHCAL.cc, src/detectors/FHCAL/FHCAL.cc",
     [("detector", "string", ""), ("capADC", "int", "counts"), ("dyRangeADC", "double", "MeV"), ("pedMeanADC", "int", "ADC"),
      ("pedSigmaADC", "double", "ADC"), ("resolutionTDC", "double", "ps"), ("thresholdValue", "double", "ADC"), ("sampFrac", "double", "")],
     [["HcalBarrel", 65536, 1000.0, 300, 2.0, 1.0, 33.0, 0.033], ["HcalEndcapN", 32768, 200.0, 10, 2.0, 10.0, 41.0, 0.0095],
      ["HcalEndcapPInsert", 32768, 200.0, 10, 2.0, 10.0, 41.0, 0.0257], ["LFHCAL", 65536, 1000.0, 50, 10.0, 10.0, 20.0, 0.037]], ["sampFrac"]),
    ("/epic/LFHCAL/sampling_fraction", "LFHCAL sampling fraction per layer: layer 0 differs from the others",
     "src/detectors/FHCAL/FHCAL.cc",
     [("rlayerz", "int", ""), ("sampFrac", "double", "")],
     [[layer, 0.019 if layer == 0 else 0.037] for layer in range(10)], ["sampFrac"]),
    ("/epic/ZDC/calib", "Zero-degree calorimeter ADC constants and HCal HEXPLIT parameters", "src/detectors/ZDC/ZDC.cc",
     [("section", "string", ""), ("capADC", "int", "counts"), ("dyRangeADC", "double", "MeV"), ("pedMeanADC", "int", "ADC"),
      ("pedSigmaADC", "double", "ADC"), ("resolutionTDC", "double", "ps"), ("thresholdFactor", "double", ""),
      ("clusterSampFrac", "double", ""), ("MIP", "double", "keV"), ("EminInMIPs", "double", ""), ("tmax", "double", "ns")],
     [["Ecal", 32768, 2000.0, 400, 3.2, 10.0, 4.0, 1.0, 0.0, 0.0, 0.0], ["Hcal", 65536, 1000.0, 400, 2.0, 10.0, 3.0, 0.0273, 630.0, 0.5, 269.0]],
     ["clusterSampFrac"]),
    ("/epic/B0ECal/adc_calib", "B0 ECal ADC constants", "src/detectors/B0ECAL/B0ECAL.cc",
     [("capADC", "int", "counts"), ("dyRangeADC", "double", "GeV"), ("pedMeanADC", "int", "ADC"), ("pedSigmaADC", "double", "ADC"),
      ("resolutionTDC", "double", "s"), ("threshold", "double", "MeV"), ("thresholdValue", "double", "ADC"), ("sampFrac", "double", ""),
      ("eResStoch", "double", "sqrt(GeV)")],
     [[16384, 170.0, 100, 1.0, 1e-11, 5.0, 1.0, 0.998, 0.0326]], ["sampFrac"]),
    ("/epic/TOFBarrel/lgad_calibration", "Barrel TOF LGAD calibration: charge = ADC*cSlope + cIntercept, time = TDC*tSlope + tIntercept",
     "src/algorithms/reco/LGADHitCalibrationConfig.h",
     [("cSlope", "double", "GeV/ADC"), ("cIntercept", "double", "GeV"), ("tSlope", "double", "ns/TDC"), ("tIntercept", "double", "ns")],
     [[1.175844e-6, 0.0, 0.024319882, 0.04314]], ["cSlope", "tSlope"]),
    ("/epic/DRICH/sipm_digi", "dRICH SiPM digitization", "src/detectors/DRICH/DRICH.cc",
     [("hitTimeWindow", "double", "ns"), ("timeResolution", "double", "ns"), ("speMean", "double", "ADC"), ("speError", "double", "ADC"),
      ("pedMean", "double", "ADC"), ("pedError", "double", "ADC"), ("safetyFactor", "double", ""), ("noiseRate", "double", "Hz")],
     [[20.0, 0.0625, 80.0, 16.0, 200.0, 3.0, 0.7, 20000.0]], ["speMean"]),
    ("/epic/DRICH/radiators", "dRICH radiators: reference refractive index, attenuation and smearing", "src/detectors/DRICH/DRICH.cc",
     [("radiator", "string", ""), ("referenceRIndex", "double", ""), ("attenuation", "double", "mm"), ("smearing", "double", "rad")],
     [["Aerogel", 1.0260, 48.0, 2e-3], ["Gas", 1.00076, 0.0, 5e-3]], []),
    ("/epic/DRICH/quantum_efficiency", "dRICH photosensor quantum efficiency by wavelength", "src/detectors/DRICH/DRICH.cc",
     [("wavelength", "double", "nm"), ("qe", "double", "")],
     [[315, 0.00], [325, 0.04], [340, 0.10], [350, 0.20], [370, 0.30], [400, 0.35], [450, 0.40], [500, 0.38], [550, 0.35],
      [600, 0.27], [650, 0.20], [700, 0.15], [750, 0.12], [800, 0.08], [850, 0.06], [900, 0.04], [1000, 0.00]], []),
    ("/epic/MPGD/digi", "MPGD digitization: threshold, time resolution, gain and strip resolution per detector", "src/detectors/MPGD/MPGD.cc",
     [("detector", "string", ""), ("threshold", "double", "eV"), ("timeResolution", "double", ""), ("gain", "double", ""),
      ("stripResolutionPhi", "double", "um"), ("stripResolutionZ", "double", "um")],
     [["MPGDBarrel", 100.0, 10.0, 10000.0, 150.0, 150.0], ["OuterMPGDBarrel", 100.0, 5.0, 10000.0, 150.0, 150.0],
      ["BackwardMPGDEndcap", 100.0, 10.0, 0.0, 0.0, 0.0], ["ForwardMPGDEndcap", 100.0, 10.0, 0.0, 0.0, 0.0]], []),
    ("/epic/RomanPots/transfer_matrix", "Roman pots static transfer matrices by nominal beam momentum (130 GeV not tuned in the source)",
     "src/detectors/RPOTS/RPOTS.cc",
     [("nomMomentum", "double", "GeV"), ("aX00", "double", ""), ("aX01", "double", ""), ("aX10", "double", ""), ("aX11", "double", ""),
      ("aY00", "double", ""), ("aY01", "double", ""), ("aY10", "double", ""), ("aY11", "double", ""), ("localXOffset", "double", ""),
      ("localYOffset", "double", ""), ("localXSlopeOffset", "double", ""), ("localYSlopeOffset", "double", "")],
     [[275.0, 3.251116, 30.285734, 0.186036375, 0.196439472, 0.4730500000, 3.062999454, 0.0204108951, -0.139318692, -1209.29, 0.00132511, -45.4772, 0.000745498],
      [130.0, 3.16912, 22.4693, 0.182402, -0.218209, 0.520743, 3.17339, 0.0222482, -0.0923779, -1209.29, 0.00132511, -45.4772, 0.000745498],
      [100.0, 3.152158, 20.852072, 0.181649517, -0.303998487, 0.5306100000, 3.19623343, 0.0226283320, -0.082666019, -1209.27, 0.00355218, -45.4737, 0.00204394],
      [41.0, 3.135997, 18.482273, 0.176479921, -0.497839483, 0.4914400000, 4.53857451, 0.0179664765, 0.004160679, -1209.22, 0.00868737, -45.4641, 0.00498786]], []),
]


def text_value(value):
    """The cell text: repr of a float keeps every digit, so the stored text is the value written above"""
    return repr(value) if isinstance(value, float) else str(value)


def period_rows(rows, columns, scaled, period_index):
    """The rows of a period: the second period scales the `scaled` columns by 1.01 (10 significant digits)"""
    names = [name for name, _, _ in columns]
    out = []
    for row in rows:
        values = list(row)
        if period_index == 1:
            for name in scaled:
                column_i = names.index(name)
                values[column_i] = float("{0:.10g}".format(values[column_i] * 1.01))
        out.append([text_value(value) for value in values])
    return out


def build(connection_string):
    """Re-creates the database and writes the demo tables into it. Returns a summary dict.

    The build runs in UTC (TZ), so the request strings that the change log records name the same times on every
    machine.
    """
    os.environ["TZ"] = "UTC"
    time.tzset()
    sys.path.insert(0, os.path.join(REPO, "python"))
    from ccdb import AlchemyProvider, testing
    from ccdb.model import (Assignment, ConstantSet, Directory, LogRecord, Property, RunRange, Tag, TypeTable, TypeTableColumn,
                            User, Variation)
    from ccdb.sql.sqlite_schema import create_sqlite_database

    if connection_string.startswith("sqlite:///"):
        create_sqlite_database(connection_string[len("sqlite:///"):])
    else:
        with contextlib.redirect_stdout(io.StringIO()):
            testing.recreate_mysql_db(connection_string)

    provider = AlchemyProvider()
    provider.connect(connection_string)
    provider.authentication.current_user_name = "test_user"
    clock = [START]

    def stamp(assignment):
        """The next minute: fixed creation times, so two builds match"""
        assignment.created = clock[0]
        clock[0] += timedelta(minutes=1)
        provider.session.commit()

    try:
        provider.create_directory("epic", "/", "ePIC calibration constants (demo, from EICrecon v1.42.0)")
        made_dirs = set()
        # `ccdb db init` holds a variation mc (child of default) already; a database without one gets it
        if "mc" not in [variation.name for variation in provider.get_variations()]:
            provider.create_variation("mc", "simulation constants: the values EICrecon uses for simulated data", "default")
        counts = {"tables": 0, "assignments": 0}
        for path, comment, source, columns, rows, scaled in TABLES:
            directory, name = path.rsplit("/", 1)
            if directory not in made_dirs:
                parent, dir_name = directory.rsplit("/", 1)
                provider.create_directory(dir_name, parent, "")
                made_dirs.add(directory)
            table = provider.create_type_table(name, directory, len(rows), columns, comment)
            provider.set_property("table", table.id, "source_url", EICRECON + source.split(",")[0].strip())
            provider.set_property("table", table.id, "procedure", "EICrecon v1.42.0 defaults; second period +1 % on: " + (", ".join(scaled) or "none"))
            counts["tables"] += 1
            for period_index, (run_min, run_max) in enumerate(PERIODS):
                stamp(provider.create_assignment(period_rows(rows, columns, scaled, period_index), path, run_min, run_max, "default",
                                                 "period {0}: runs {1}-{2}".format(period_index + 1, run_min, run_max)))
                counts["assignments"] += 1
            # simulation: the EICrecon values for every run
            stamp(provider.create_assignment(period_rows(rows, columns, [], 0), path, 0, 2147483647, "mc", "EICrecon v1.42.0 defaults"))
            counts["assignments"] += 1

        # a resources table: a model file on CVMFS, by url, sha256 and size
        provider.create_type_table("pi_rejection_model", "/epic/EcalEndcapN", 1, [("url", "string"), ("sha256", "string"), ("size", "int")],
                                   "EEEMCal pion rejection ONNX model (EcalEndcapN_pi_rejection.onnx)")
        stamp(provider.create_assignment([[RESOURCE_PATH, hashlib.sha256(RESOURCE_BYTES).hexdigest(), str(len(RESOURCE_BYTES))]],
                                         "/epic/EcalEndcapN/pi_rejection_model", 0, 2147483647, "default", "model of the 2026 run"))
        counts["tables"] += 1
        counts["assignments"] += 1

        provider.create_tag("campaign_demo", "default", TAG_TIME, "demo reconstruction campaign: constants before the late correction")
        # the late correction: the barrel TOF time offset of the second period, after the tag
        clock[0] = TAG_TIME + timedelta(days=3)
        late = period_rows(TABLES[8][4], TABLES[8][3], TABLES[8][5], 1)
        late[0][3] = text_value(0.05114)
        stamp(provider.create_assignment(late, "/epic/TOFBarrel/lgad_calibration", 1000, 1999, "default", "late correction of tIntercept"))
        counts["assignments"] += 1

        for name, value in (("experiment", "ePIC (demo)"), ("description", "ePIC-shaped demo constants from EICrecon v1.42.0 defaults"),
                            ("license", "LGPL-3.0-or-later (the values come from EICrecon, LGPL-3.0)"),
                            ("contact", "ccdb maintainers"), ("url", "https://jeffersonlab.github.io/ccdb/#/get-started/demo")):
            provider.set_property("instance", 0, name, value)

        # The provider stamps every other object with the current time; fix those times too, so two builds match
        for record_i, record in enumerate(provider.session.query(LogRecord).order_by(LogRecord.id).all()):
            record.created = START + timedelta(seconds=record_i)
            # "Created assignment '<request with the write time>'": the time of the assignment, in the record and in its
            # request string
            named = re.search(r"\|assignments(\d+)\|", record.affected_ids or "")
            if named and record.description and record.description.startswith("Created assignment '"):
                assignment = provider.session.get(Assignment, int(named.group(1)))
                record.created = assignment.created
                record.description = re.sub(r"'[^']*'", lambda _: "'" + assignment.request + "'", record.description, count=1)
        for model in (Directory, TypeTable, TypeTableColumn, Variation, RunRange, ConstantSet, User, Property):
            for obj in provider.session.query(model).all():
                for attribute in ("created", "modified", "last_action_time", "lock_time"):
                    if getattr(obj, attribute, None) is not None:
                        setattr(obj, attribute, START)
        for assignment in provider.session.query(Assignment).all():
            assignment.modified = assignment.created
        for tag in provider.session.query(Tag).all():
            tag.created = TAG_TIME
        provider.session.commit()
        counts["newest_assignment"] = str(provider.session.query(Assignment).order_by(Assignment.id.desc()).first().created)
        return counts
    finally:
        provider.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Write the ePIC-shaped demo tables into a fresh CCDB database")
    parser.add_argument("connection", help="sqlite:///path or mysql://user@host/database; it is re-initialized")
    summary = build(parser.parse_args().connection)
    print(summary)


if __name__ == "__main__":
    main()
