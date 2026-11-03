# CCDB and DD4hep, step by step

This page builds one small detector whose geometry numbers, gains and alignment all live in CCDB, and runs a
job that reads them through DD4hep for a given run. Everything on it is run by CI exactly as written
(`scripts/eic/dd4hep_example.sh`), so the commands and the printed numbers are real. What you take away: how
to lay out tables for DD4hep, how constants go in, and the twenty lines a job needs to get them out.

The pieces (reference: [DD4hep plugins](apis/dd4hep.md)):

- `CCDB_Constants` runs while DD4hep reads the compact XML and defines constants from a one-row CCDB table, so
  the geometry is built from calibrated numbers.
- `CCDB_ConditionsLoader` is the loader of DD4hep's conditions manager: for the run a job processes it reads
  CCDB tables, one row per detector element, and hands them to DD4hep as conditions; alignment rows become
  `Delta` objects that DD4hep turns into aligned positions.

## 1. Build CCDB with the DD4hep plugins

The plugins need DD4hep 1.38 or newer and ROOT. The ePIC software image has both; on a host with docker:

```bash
git clone https://github.com/JeffersonLab/ccdb.git && cd ccdb
scripts/eic/run_in_eic_shell.sh bash              # eic-shell with this checkout mounted at /ccdb
```

Inside (or on any machine where `find_package(DD4hep)` works):

```bash
cmake -S cpp -B build -DCCDB_BUILD_DD4HEP=ON
cmake --build build --target ccdb_dd4hep Components_ccdb_dd4hep ccdb_dd4hep_example -j8
export LD_LIBRARY_PATH="$PWD/build/lib/CCDB/dd4hep:$LD_LIBRARY_PATH"
```

`libccdb_dd4hep.so` holds both plugins and `libccdb_dd4hep.components` is how DD4hep's plugin manager finds
them: the directory that holds the two must be on `LD_LIBRARY_PATH` for any program that does not link the
library itself. `ccdb_dd4hep_example` is the job of step 5. `cmake --install build` puts the library, the
components file and `CCDB/DD4hep/CCDB_DD4hep.h` into the prefix.

The `ccdb` command comes with the Python package (`pip install ccdb`); in the image, the checkout's package works
without installing: `alias ccdb='PYTHONPATH=/ccdb/python python3 -m ccdb'`.

## 2. A database and the tables

A SQLite file is a complete CCDB database. The three tables of the detector:

```bash
export CCDB_CONNECTION=sqlite:///$PWD/ccdb.sqlite
ccdb db init --init-i-am-sure
ccdb user --create calib                               # the author of what follows (ccdb -u calib …)

ccdb mkdir /epic "#ePIC"
ccdb mkdir /epic/EcalBarrel "#Barrel ECal"
ccdb mktbl /epic/EcalBarrel/geometry  -r 1 inner_radius=double:mm outer_radius=double:mm length=double:mm n_sectors=int material=string "#Barrel ECal envelope"
ccdb mktbl /epic/EcalBarrel/gains     -r 2 element=string gain=double pedestal=double:ADC "#Barrel ECal gain and pedestal per module"
ccdb mktbl /epic/EcalBarrel/alignment -r 2 element=string dx=double:mm dy=double:mm dz=double:mm dphi=double:rad dtheta=double:rad dpsi=double:rad "#Barrel ECal module alignment"
```

Three shapes, three uses:

| table | rows | key | read by |
|---|---|---|---|
| `geometry` | one | none | `CCDB_Constants`, while the compact file is parsed: each column becomes a constant |
| `gains` | one per module | `element`, the module's DD4hep path | `CCDB_ConditionsLoader`, as a `map<string, double>` condition per module |
| `alignment` | one per module | `element` | `CCDB_ConditionsLoader`, as a `Delta` condition per module (the column names `dx dy dz dphi dtheta dpsi` are what makes it one) |

`name=type:units` records the units with the column; `CCDB_Constants` uses them (`105.5*mm`) and `info`, the
web GUI, the API and the exports show them. The CCDB paths are yours: the DD4hep element path appears only as a
value in the `element` column, never as a directory.

## 3. The constants

Text files, one row per line, columns in the table's order:

```
geometry.txt           105.5 160 340 48 PbWO4
gains_2026a.txt        /world/EcalBarrel/module_1 1.10 5
                       /world/EcalBarrel/module_2 1.20 6
gains_2026b.txt        /world/EcalBarrel/module_1 1.12 5
                       /world/EcalBarrel/module_2 1.25 7
alignment_nominal.txt  /world/EcalBarrel/module_1 0 0 0 0 0 0
                       /world/EcalBarrel/module_2 0 0 0 0 0 0
alignment_2026b.txt    /world/EcalBarrel/module_1 1.0 0 -3.0 0 0 0.01
                       /world/EcalBarrel/module_2 0.5 0  0   0 0 0
```

Each `add` assigns a file's rows to a run range; the comment says why:

```bash
ccdb add /epic/EcalBarrel/geometry  -r 0-        geometry.txt          "#from the survey of 2026"
ccdb add /epic/EcalBarrel/gains     -r 1-999     gains_2026a.txt       "#spring 2026 calibration"
ccdb add /epic/EcalBarrel/gains     -r 1000-1999 gains_2026b.txt       "#after the HV change"
ccdb add /epic/EcalBarrel/alignment -r 1-        alignment_nominal.txt "#nominal"
ccdb add /epic/EcalBarrel/alignment -r 1000-     alignment_2026b.txt   "#survey after the access of week 40"
```

A production freezes what it reads with a [tag](concepts/tags.md), a name for the variation at a moment. A
recalibration added afterwards is a new version that the tag does not see:

```bash
ccdb tag pass1 -v default -t 2026-11-03-09-03-25 -c "first pass"       # a past moment, local wall time: after the adds above, before the one below
ccdb add /epic/EcalBarrel/gains -r 1000-1999 gains_2026c.txt "#recalibrated after pass 1"   # 1.14 and 1.27
```

What the database holds now, and what two requests give:

```
$ ccdb vers /epic/EcalBarrel/gains
(ID)     (created)              (user)           (variation)     (run range)      (comments)
 11      2026-11-03 09-03-28    calib            default         1000-1999       recalibrated after p
 8       2026-11-03 09-03-22    calib            default         1000-1999       after the HV change
 7       2026-11-03 09-03-20    calib            default         1-999           spring 2026 calibrat
$ ccdb cat /epic/EcalBarrel/gains:1500
+--------------------------------------+
| element    | gain       | pedestal   |
| string     | double     | double     |
+--------------------------------------+
| /world/EcalBarrel/module_1 | 1.14       | 5          |
| /world/EcalBarrel/module_2 | 1.27       | 7          |
+--------------------------------------+
$ ccdb cat /epic/EcalBarrel/gains:1500@pass1
+--------------------------------------+
| element    | gain       | pedestal   |
| string     | double     | double     |
+--------------------------------------+
| /world/EcalBarrel/module_1 | 1.12       | 5          |
| /world/EcalBarrel/module_2 | 1.25       | 7          |
+--------------------------------------+
```

Nothing was overwritten: run 1500 has three versions of `gains`, the newest answers a plain request, the one
before the tag answers `@pass1`, and runs 1–999 keep the spring calibration.

## 4. The geometry file

A compact file with DD4hep's elements and materials, a world, and the CCDB plugin in `<properties>`, which
DD4hep processes before any detector:

```xml
<lccdd>
  <geometry open="true" close="false"/>                 <!-- the program adds volumes after reading this file -->
  <std_conditions type="NTP"/>                          <!-- material conditions: normal temperature and pressure -->
  <includes>
    <gdmlFile ref="${DD4hepINSTALL}/DDDetectors/compact/elements.xml"/>
    <gdmlFile ref="${DD4hepINSTALL}/DDDetectors/compact/materials.xml"/>
  </includes>
  <define>
    <constant name="world_side" value="10*m"/>
    <constant name="world_x" value="world_side"/>
    <constant name="world_y" value="world_side"/>
    <constant name="world_z" value="world_side"/>
  </define>
  <materials>
    <material name="PbWO4">                              <!-- lead tungstate, the crystal of the barrel ECal -->
      <D value="8.28" unit="g/cm3"/>
      <composite n="1" ref="Pb"/>
      <composite n="1" ref="W"/>
      <composite n="4" ref="O"/>
    </material>
  </materials>
  <properties>
    <plugin name="CCDB_Constants" type="xml" table="/epic/EcalBarrel/geometry" run="1" prefix="ecal_"/>
  </properties>
</lccdd>
```

`CCDB_Constants` opens `$CCDB_CONNECTION` (or its `url=` attribute), reads the row of `/epic/EcalBarrel/geometry`
for run 1 (newest; `tag="pass1"` or `variation=`/`time=` pin it), and defines `ecal_inner_radius = 105.5*mm`,
`ecal_outer_radius`, `ecal_length`, `ecal_n_sectors = 48` and the string `ecal_material = PbWO4`, using each
column's units. A detector's own XML then uses them like any constant (`<dimensions rmin="ecal_inner_radius" …/>`);
the example program reads them from C++ instead, which is what a detector constructor does.

## 5. The job

`dd4hep/examples/ccdb_dd4hep_example.cc`, in full on
[GitHub](https://github.com/JeffersonLab/ccdb/blob/v2-main/dd4hep/examples/ccdb_dd4hep_example.cc); the parts
that matter:

**Geometry from the constants.** Reading the compact file runs the plugin; the constants are then plain DD4hep
constants, and the two modules are placed at the inner radius:

```cpp
auto& detector = dd4hep::Detector::getInstance();
detector.fromXML(compact);
const double inner  = detector.constant<double>("ecal_inner_radius");     // 105.5 mm
const double outer  = detector.constant<double>("ecal_outer_radius");     // 160 mm
const double length = detector.constant<double>("ecal_length");
const std::string material = detector.constantAsString("ecal_material"); // PbWO4

dd4hep::DetElement ecal(detector.world(), "EcalBarrel", 1);
dd4hep::Volume envelope("EcalBarrel_envelope", dd4hep::Tube(inner, outer, length / 2), detector.air());
ecal.setPlacement(detector.worldVolume().placeVolume(envelope));
dd4hep::Volume module_volume("module", dd4hep::Box((outer - inner) / 2, 10 * dd4hep::cm, length / 2), detector.material(material));
for (int number : {1, 2}) {
    double x = (number == 1 ? 1 : -1) * (inner + (outer - inner) / 2);        // ±132.75 mm, the middle of the crystal
    dd4hep::PlacedVolume placed = envelope.placeVolume(module_volume, dd4hep::Position(x, 0, 0));
    modules[number] = dd4hep::DetElement(ecal, "module_" + std::to_string(number), number);   // /world/EcalBarrel/module_1
    modules[number].setPlacement(placed);
}
detector.endDocument();
```

**The conditions manager with CCDB as its loader**, and the content that says which table holds which
condition of which module:

```cpp
detector.apply("DD4hep_ConditionsManagerInstaller", 0, nullptr);
auto manager = dd4hep::cond::ConditionsManager::from(detector);
manager["PoolType"]       = "DD4hep_ConditionsLinearPool";
manager["UserPoolType"]   = "DD4hep_ConditionsMapUserPool";
manager["UpdatePoolType"] = "DD4hep_ConditionsLinearUpdatePool";
manager["LoaderType"]     = "CCDB_ConditionsLoader";
manager.initialize();
manager.loader()["URL"] = std::string(getenv("CCDB_CONNECTION"));
if (!tag.empty()) manager.loader()["Tag"] = tag;                     // else the newest; or Variation and Time
const dd4hep::IOVType* runs = manager.registerIOVType(0, "run").second;

auto content = std::make_shared<dd4hep::cond::ConditionsContent>();
for (auto& entry : modules) {
    ccdb::dd4hep_plugins::AddCondition(*content, entry.second, "gains",                       "/epic/EcalBarrel/gains");
    ccdb::dd4hep_plugins::AddCondition(*content, entry.second, dd4hep::align::Keys::deltaName, "/epic/EcalBarrel/alignment");
}
```

**One run: prepare, read, align.** `prepare` asks the loader for everything the slice lacks for that run; the
loader reads each table once and picks each module's row:

```cpp
dd4hep::cond::ConditionsSlice slice(manager, content);
manager.prepare(dd4hep::IOV(runs, run), slice);

std::map<dd4hep::DetElement, dd4hep::Delta> deltas;
for (auto& entry : modules)
    deltas[entry.second] = slice.get(entry.second, dd4hep::align::Keys::deltaKey).get<dd4hep::Delta>();
dd4hep::align::AlignmentsCalculator().compute(deltas, slice);          // deltas → aligned transformations

for (auto& entry : modules) {
    const auto& gains = slice.get(module, dd4hep::ConditionKey::itemCode("gains")).get<std::map<std::string, double>>();
    dd4hep::Alignment aligned = slice.get(module, dd4hep::align::Keys::alignmentKey);
    const double* position = aligned.worldTransformation().GetTranslation();
    // gains.at("gain"), gains.at("pedestal"), deltas[module].translation, position[0], position[2]
}
```

Run it for a run in the first period, one in the second, and the second under the tag:

```bash
./build/dd4hep/ccdb_dd4hep_example ecal.xml 500
./build/dd4hep/ccdb_dd4hep_example ecal.xml 1500
./build/dd4hep/ccdb_dd4hep_example ecal.xml 1500 pass1
```

```
$ ./build/dd4hep/ccdb_dd4hep_example ecal.xml 500
geometry: inner_radius=105.5 mm outer_radius=160 mm length=340 mm n_sectors=48 material=PbWO4
run 500:
  /world/EcalBarrel/module_1   gain=1.1 pedestal=5 ADC  delta dx=0 dz=0 mm dpsi=0 rad  aligned x=132.75 z=0 mm
  /world/EcalBarrel/module_2   gain=1.2 pedestal=6 ADC  delta dx=0 dz=0 mm dpsi=0 rad  aligned x=-132.75 z=0 mm
$ ./build/dd4hep/ccdb_dd4hep_example ecal.xml 1500
geometry: inner_radius=105.5 mm outer_radius=160 mm length=340 mm n_sectors=48 material=PbWO4
run 1500:
  /world/EcalBarrel/module_1   gain=1.14 pedestal=5 ADC  delta dx=1 dz=-3 mm dpsi=0.01 rad  aligned x=133.75 z=-3 mm
  /world/EcalBarrel/module_2   gain=1.27 pedestal=7 ADC  delta dx=0.5 dz=0 mm dpsi=0 rad  aligned x=-132.25 z=0 mm
$ ./build/dd4hep/ccdb_dd4hep_example ecal.xml 1500 pass1
geometry: inner_radius=105.5 mm outer_radius=160 mm length=340 mm n_sectors=48 material=PbWO4
run 1500 tag pass1:
  /world/EcalBarrel/module_1   gain=1.12 pedestal=5 ADC  delta dx=1 dz=-3 mm dpsi=0.01 rad  aligned x=133.75 z=-3 mm
  /world/EcalBarrel/module_2   gain=1.25 pedestal=7 ADC  delta dx=0.5 dz=0 mm dpsi=0 rad  aligned x=-132.25 z=0 mm
```

Where each number came from:

| printed | from |
|---|---|
| `inner_radius=105.5 mm … material=PbWO4` | the one row of `geometry`, through `CCDB_Constants`, with the columns' units |
| run 500, `gain=1.1`, `delta dx=0`, `aligned x=132.75` | `gains_2026a.txt` (runs 1–999) and `alignment_nominal.txt`; the nominal position is `inner + (outer − inner)/2` |
| run 1500, `gain=1.14`, `dx=1 dz=-3 dpsi=0.01`, `aligned x=133.75 z=-3` | the newest `gains` for 1000–1999 (`gains_2026c.txt`) and `alignment_2026b.txt`; the aligned position is the nominal one moved by the delta |
| run 1500 under `pass1`, `gain=1.12` | the `gains` version before the tag's moment (`gains_2026b.txt`); the alignment is the same, it did not change after the tag |

## 6. The same from a framework

A reconstruction job does the same three things once at start-up (manager, loader properties, content) and
`prepare` at each run change. The loader's properties are the production's context: `URL` is any connection
string the C++ library opens (`mysql://`, `sqlite://`, or the [HTTP API](apis/cpp.md#http-api) `https://host/api/v1`,
where a job downloads one SQLite bundle per run), and either `Tag` or `Variation` and `Time`. A simulation
production sets `Variation` to `mc` and reads the run numbers of the period it simulates. JANA2 jobs that read
per-event constants keep using the [JANA2 service](apis/jana.md); the two share the database and the tags.

## 7. From the example to your detector

- **The key column.** The loader matches `element` against the module's full DD4hep path. A short name or the
  element's id would be a one-line change in the loader; settle it with the first real table.
- **Which tables are conditions.** Only what DD4hep asks per element needs the `element` column. Numbers the
  geometry needs are a one-row table for `CCDB_Constants`; per-event constants go through the JANA2 service.
- **Many modules.** One table holds all modules of a detector (one row each); the loader reads it once per run.
  A change for one module is a new version of the whole table, which is how CCDB keeps history.
- **Large payloads.** A condition is a row of numbers and text. A field map or a model file is a resources row
  (URL, SHA-256, size) that the JANA2 service fetches and checks.
- **Validity.** Today a loaded condition is valid for the requested run; jobs that cross runs reload at each
  change (Q60 in the plan extends it to the assignment's run range).
