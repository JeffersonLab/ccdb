# Demo

The demo runs CCDB on one machine with calibration tables shaped like those of the ePIC experiment: a database,
the [HTTP API](apis/http.md) behind its cache, the web GUI, and a JANA2 application that reads its constants through
the [JANA2 service](apis/jana.md), once by variation and run and once by a campaign [tag](concepts/tags.md).

## The demo tables

`scripts/demo/make_epic_tables.py` writes fifteen tables under `/epic` with the names, shapes and values of the
calibration constants that EICrecon v1.42.0 reads today: calorimeter ADC constants and sampling fractions, the barrel
TOF calibration, RICH digitization and radiators, MPGD digitization, Roman pots transfer matrices, and a resources
table for an ONNX model. Each table's `source_url` property names the EICrecon file the values come from.

The tables show how constants change:

- **By run.** Runs 1–999 and 1000–1999 have their own assignments; in the second period the gains and sampling
  fractions are 1 % higher, so a job that crosses run 1000 reads new constants.
- **By variation.** `mc`, a child of `default`, holds EICrecon's values for every run, for simulation.
- **By campaign.** The tag `campaign_demo` freezes the constants of 1 February 2026. A late correction of the barrel
  TOF time offset for runs 1000–1999 comes after it: a request without the tag reads the correction, one with the tag
  reads the value before it.

```bash
python scripts/demo/make_epic_tables.py sqlite:///epic_demo.sqlite
ccdb -c sqlite:///epic_demo.sqlite cat /epic/TOFBarrel/lgad_calibration:1500
ccdb -c sqlite:///epic_demo.sqlite cat /epic/TOFBarrel/lgad_calibration:1500@campaign_demo
```

Two builds of the database hold the same rows: every time and value is fixed.

## The services

`docker/demo/compose.yml` starts MariaDB with the demo tables, the HTTP API behind nginx with the shipped cache
configuration, and the web GUI:

```bash
docker compose -f docker/demo/compose.yml up --build -d
python scripts/demo/check.py
docker compose -f docker/demo/compose.yml down -v
```

- `http://localhost:8080/api/v1/docs`: the API, through the cache;
- `http://localhost:5000`: the web GUI;
- `127.0.0.1:3306`: the database, `mysql://root@127.0.0.1:3306/ccdb_demo`, for the JANA2 application.

Every port listens on the loopback interface. When one is taken, set `CCDB_DEMO_API_PORT`, `CCDB_DEMO_GUI_PORT`
or `CCDB_DEMO_DB_PORT`, and give `check.py` the same ports: `--api http://localhost:18080 --gui http://localhost:15000`.

`check.py` waits for the services, requests the demo's URLs and checks the answers, among them the run bundle of the
campaign tag. The database's root user has no password and its port is bound to the loopback interface: the compose
file is for one machine.

## The JANA2 application

`jana2/examples/epic_demo/ccdb_epic_demo.cc` is a JANA2 application with an event source of two runs, 500 and 1500,
and a processor that reads `/epic/TOFBarrel/lgad_calibration` and `/epic/HCal/adc_calib` at each run change, as a
factory does in `ChangeRun()`. It is built with the JANA2 service (`-DCCDB_BUILD_JANA2=ON`). The `eic-shell` image has no MySQL client library, so
CCDB built there reads SQLite files; give the application the demo tables as a file:

```bash
python scripts/demo/make_epic_tables.py sqlite:///epic_demo.sqlite
ccdb_epic_demo sqlite:///$PWD/epic_demo.sqlite
ccdb_epic_demo sqlite:///$PWD/epic_demo.sqlite campaign_demo
```

Where CCDB is built with a MySQL client, the application reads the demo database of the compose stack the same way:
`ccdb_epic_demo mysql://root@127.0.0.1:3306/ccdb_demo`.

The first run prints the constants of each period, the late TOF correction included; the second prints the
constants of the campaign:

```
run 500  /epic/TOFBarrel/lgad_calibration  cSlope=1.175844e-06  tSlope=0.024319882  tIntercept=0.04314
run 1500  /epic/TOFBarrel/lgad_calibration  cSlope=1.18760244e-06  tSlope=0.02456308082  tIntercept=0.05114
```

## EICrecon

In EICrecon, a factory reads its constants in `ChangeRun()` through the service. The demo patches
`LGADHitCalibration_factory`, the barrel TOF calibration, to read `cSlope`, `cIntercept`, `tSlope` and `tIntercept`
from the table its parameter `ccdbTable` names, and keeps the parameters as they are when the table is not set.
[Use the service in EICrecon](apis/jana.md#use-the-service-in-eicrecon) lists the build steps.
