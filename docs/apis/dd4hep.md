# DD4hep plugins

The library `ccdb_dd4hep` brings CCDB constants into a [DD4hep](https://dd4hep.web.cern.ch) detector
description in two ways:

- **`CCDB_Constants`** defines compact XML constants from a one-row CCDB table while the compact file is
  read, so the geometry can use calibrated dimensions in its expressions.
- **`CCDB_ConditionsLoader`** is a DDCond conditions loader: the conditions of detector elements, alignment
  deltas included, come from CCDB tables for the run of the requested interval of validity.

Build them with `-DCCDB_BUILD_DD4HEP=ON` where DD4hep is installed (eic-shell has it; tested with DD4hep 1.38).
DD4hep finds the plugins through `libccdb_dd4hep.components`, written next to the library, so the directory that
holds both must be on `LD_LIBRARY_PATH`. A program links nothing of CCDB: the header `CCDB_DD4hep.h` is inline and
the plugin manager loads the library when a plugin is first used.

```bash
cmake -S cpp -B build -DCCDB_BUILD_DD4HEP=ON && cmake --build build --target ccdb_dd4hep Components_ccdb_dd4hep
export LD_LIBRARY_PATH=$PWD/build/lib/CCDB/dd4hep:$LD_LIBRARY_PATH
```

## Constants in compact XML

```xml
<properties>
  <plugin name="CCDB_Constants" type="xml" table="/epic/geometry/ecal_dims" run="1" prefix="ecal_" units="mm">
    <unit column="n_sectors" value=""/>
  </plugin>
</properties>
```

DD4hep reads `<properties>` before the detectors, so `ecal_inner_radius` and its siblings can be used in any
detector's XML. Each column of the table's single row becomes one constant named prefix + column. A number
becomes `(value)*units`, so the evaluator converts it to DD4hep's units; a text column becomes a string constant.

| attribute | default | meaning |
|---|---|---|
| `table` | required | the CCDB table; it must resolve to one row |
| `run` | `0` | the run whose constants are read |
| `url` | `$CCDB_CONNECTION`, then `$JANA_CALIB_URL` | the connection string, any the C++ library opens (`sqlite://`, `mysql://`, `https://…/api/v1`) |
| `variation`, `time` | `default`, the newest | as `ccdb:variation` and `ccdb:time` of the [JANA2 service](apis/jana.md) |
| `tag` | none | a [tag](concepts/tags.md) instead of variation and time |
| `prefix` | none | prepended to every constant's name |
| `units` | the columns' own units | units of every number column, e.g. `mm` |
| `<unit column= value=/>` | | the units of one column, overriding `units` and the column's own; an empty value means none |

Without `units` and `<unit>` the units stored with each column apply (`mktbl inner_radius=double:mm`), so a
well-described table needs no units in the XML.

A table of geometry constants has one row and one column per constant:

```
ccdb mktbl /epic/geometry/ecal_dims -r 1 inner_radius=double:mm outer_radius=double:mm n_sectors=int material=string
```

## Conditions of detector elements

A table of conditions has one row per detector element: a text column `element` with the element's path
(`/world/EcalBarrel/module_3`), and the values. An alignment table has the columns `dx`, `dy`, `dz` and
`dphi`, `dtheta`, `dpsi`:

```
ccdb mktbl /epic/alignment/ecal -r 64 element=string dx=double:mm dy=double:mm dz=double:mm dphi=double:rad dtheta=double:rad dpsi=double:rad
```

Install the loader as the conditions manager's loader, tell a `ConditionsContent` which table holds each
condition, and prepare slices as usual:

```cpp
#include <CCDB_DD4hep.h>          // AddCondition, and DDCond's ConditionsManager, ConditionsContent, ConditionsDataLoader
#include <DD4hep/Detector.h>
#include <DD4hep/Alignments.h>    // dd4hep::align::Keys

detector.apply("DD4hep_ConditionsManagerInstaller", 0, nullptr);
dd4hep::cond::ConditionsManager manager = dd4hep::cond::ConditionsManager::from(detector);
manager["PoolType"] = "DD4hep_ConditionsLinearPool";
manager["UserPoolType"] = "DD4hep_ConditionsMapUserPool";
manager["UpdatePoolType"] = "DD4hep_ConditionsLinearUpdatePool";
manager["LoaderType"] = "CCDB_ConditionsLoader";
manager.initialize();
manager.loader()["URL"] = std::string("sqlite:////cvmfs/example.org/ccdb/ccdb.sqlite");
const dd4hep::IOVType* runs = manager.registerIOVType(0, "run").second;

auto content = std::make_shared<dd4hep::cond::ConditionsContent>();
ccdb::dd4hep_plugins::AddCondition(*content, module, dd4hep::align::Keys::deltaName, "/epic/alignment/ecal");
ccdb::dd4hep_plugins::AddCondition(*content, module, "gains", "/epic/ECal/gains");

dd4hep::cond::ConditionsSlice slice(manager, content);
manager.prepare(dd4hep::IOV(runs, run), slice);
const auto& gains = slice.get(module, dd4hep::ConditionKey::itemCode("gains")).get<std::map<std::string, double>>();
```

The item `dd4hep::align::Keys::deltaName` becomes a `dd4hep::Delta` flagged as an alignment delta, which
`dd4hep::align::AlignmentsCalculator` turns into the element's alignment; any other item becomes a
`std::map<std::string, double>` of the row's number columns.

| loader property | default | meaning |
|---|---|---|
| `URL` | `$CCDB_CONNECTION`, then `$JANA_CALIB_URL` | the connection string |
| `Variation`, `Time` | `default`, the newest | the context of every run |
| `Tag` | none | a tag instead |
| `LengthUnit`, `AngleUnit` | `mm`, `rad` | the units of the alignment columns |

The interval of validity of a loaded condition is the requested run: the C++ library does not report the
run range of an assignment, so the next run loads again, from a `Calibration` the loader keeps per run.

## How DD4hep conditions work, and how CCDB maps onto them

DD4hep's detector description is a tree of `DetElement`s. A *condition* is any payload object attached to one
element under an item name, together with an *interval of validity* (IOV) in a unit the experiment chooses. The
framework's `ConditionsManager` keeps pools of conditions per IOV; a job *prepares a slice* for the IOV it is
processing, and whatever the pools lack is requested from the experiment's loader in one call. Derived
conditions, alignment among them, are computed from loaded ones by callbacks. The snippets below are DD4hep's
own (`examples/AlignDet` and `examples/Conditions` of DD4hep 1.38) and this library's tests.

**A condition is any payload.** The condition object is a handle; `bind<T>()` gives it a `T`. DD4hep's
alignment example binds a `Delta`; its conditions example binds `std::vector<int>`; CCDB's loader binds a `Delta`
for the alignment item and `std::map<std::string, double>` for every other table row.

```cpp
Condition cond(de.path() + "#" + align::Keys::deltaName, align::Keys::deltaName);
Delta& delta = cond.bind<Delta>();                                   // the payload type
cond->hash = ConditionKey(de.key(), align::Keys::deltaKey).hash;     // (detector element, item) is the key
cond->setFlag(Condition::ACTIVE | Condition::ALIGNMENT_DELTA);
delta.translation.SetZ(delta.translation.Z() + 0.1 * dd4hep::cm);
delta.flags |= Delta::HAVE_TRANSLATION | Delta::HAVE_ROTATION;
manager.registerUnlocked(pool, cond);                                // into the pool of one IOV
```

**The experiment chooses what validity means.** An IOV type is a number and a name; DD4hep has no opinion
whether it is a run, a timestamp or a fill. CCDB's run model is the `"run"` type:

```cpp
const IOVType* iov_typ = manager.registerIOVType(0, "run").second;
IOV iov(iov_typ, IOV::Key(1001, 2000));                              // runs 1001–2000
ConditionsPool* pool = manager.registerIOV(*iov.iovType, iov.key());
```

**Preparing a slice.** A `ConditionsContent` declares which conditions a slice holds and where each comes from;
`prepare` fills the slice for one IOV, calling the loader's `load_many(required IOV, missing items)` for what the
pools lack, which is the one method `CCDB_ConditionsLoader` implements:

```cpp
manager["LoaderType"] = "CCDB_ConditionsLoader";                     // before initialize()
manager.initialize();
manager.loader()["URL"] = connection;
auto content = std::make_shared<cond::ConditionsContent>();
ccdb::dd4hep_plugins::AddCondition(*content, module, "gains", "/epic/EcalBarrel/gains");
cond::ConditionsSlice slice(manager, content);
manager.prepare(IOV(iov_typ, 1500), slice);                          // run 1500
auto& gains = slice.get(module, ConditionKey::itemCode("gains")).get<std::map<std::string, double>>();
```

**Derived conditions through callbacks.** A dependency names a target, its inputs and a `ConditionUpdateCall`
that creates the payload and fills it from the inputs; `prepare` runs the callbacks in dependency order with the
intersection of the inputs' IOVs as validity. Alignment is this machinery packaged:
`AlignmentsCalculator::compute(deltas, slice)` turns `Delta` conditions into `Alignment` conditions, the
transformation matrices reconstruction asks for.

```cpp
Condition MyCall::operator()(const ConditionKey& key, ConditionUpdateContext&) {
    Condition target(key.hash);
    target.bind<std::vector<int>>();                                   // create the derived payload
    return target;
}
void MyCall::resolve(Condition target, ConditionUpdateContext& context) {
    auto& data = target.get<std::vector<int>>();
    data.push_back(context.condition(context.key(0)).get<int>());      // from the inputs of this IOV
}
DependencyBuilder build(de, ConditionKey(de, "derived").item_key(), std::make_shared<MyCall>());
build.add(ConditionKey(de, "raw"));
content.addDependency(build.release());
```

### The mapping onto CCDB

What the loader receives is a list of `(element, item, IOV)`; what CCDB stores is tables of typed rows assigned
to run ranges in variations. The two meet like this, with nothing added to CCDB's schema:

| DD4hep | CCDB |
|---|---|
| item (`"gains"`, `align::Keys::deltaName`) | a table, named by the experiment in `AddCondition(content, element, item, table)` |
| element (`/world/EcalBarrel/module_1`) | a row of that table: the text column `element` holds the element's path, the other columns the values |
| the payload | the row's numeric columns as `map<string, double>`, or `dx dy dz dphi dtheta dpsi` as a `Delta` |
| IOV (run 1500) | the assignment of the table that covers the run, resolved as `ccdb cat` resolves it: variation with its parents, created at or before the time, or under the tag |
| validity returned | the run (the assignment's run range once the C++ short query returns it, Q60) |

The DD4hep tree does not shape the CCDB tree: the element path is a value in a column, the table path is
whatever the detector's directory is (`/epic/EcalBarrel/gains`), and the mapping between the two is the
`AddCondition` lines in the code that knows both, the detector's own plugin. One table can serve all modules of a
detector; a table needs the `element` column only when DD4hep asks per element, so the geometry numbers of
`CCDB_Constants` are a one-row table without it.

What CCDB adds over a file of conditions is its history and context: a new alignment for runs 1000 onward is a
new assignment and the old one stays, `mc` can carry its own alignment for simulation, and a tag gives a
campaign the conditions as they were when it was frozen, all through the loader's `URL`, `Variation`/`Time` or
`Tag` properties.

## Worked example: from `ccdb add` to a DD4hep job

The whole path for one detector, the barrel ECal: a calibrator describes and fills three tables, a tag freezes
them for a production, the geometry reads one table while the compact file is parsed, and a job reads the other
two as conditions for its run. Every command below was run as shown; the tables are the ones the
[tests](https://github.com/JeffersonLab/ccdb/tree/v2-main/dd4hep/tests) use, with ePIC names.

### 1. The calibrator describes the tables

Three tables under the detector's directory. `geometry` has one row and no key column: numbers the geometry
needs, each with its units. `gains` and `alignment` have one row per detector element: a text column `element`
with the element's DD4hep path, then the values. The CCDB paths are the experiment's choice; the DD4hep paths
appear only inside the rows.

```bash
export CCDB_CONNECTION=mysql://ccdb_calib@dbhost/ccdb        # or sqlite:////path/ccdb.sqlite
ccdb mkdir /epic/EcalBarrel "#Barrel ECal"
ccdb mktbl /epic/EcalBarrel/geometry  -r 1 inner_radius=double:mm outer_radius=double:mm length=double:mm n_sectors=int material=string "#Barrel ECal envelope"
ccdb mktbl /epic/EcalBarrel/gains     -r 2 element=string gain=double pedestal=double:ADC "#Barrel ECal gain and pedestal per module"
ccdb mktbl /epic/EcalBarrel/alignment -r 2 element=string dx=double:mm dy=double:mm dz=double:mm dphi=double:rad dtheta=double:rad dpsi=double:rad "#Barrel ECal module alignment"
```

(`-r 2`: two rows, one per module in this small example; a real table has as many rows as elements.)

### 2. The calibrator adds constants

Plain text files, one row per line, columns in the table's order:

```
# geometry.txt                     # gains_2026a.txt                      # alignment_2026b.txt
105.5 160 340 48 PbWO4             /world/EcalBarrel/module_1 1.10 5     /world/EcalBarrel/module_1 1.0 0 -3.0 0 0 0.01
                                   /world/EcalBarrel/module_2 1.20 6     /world/EcalBarrel/module_2 0.5 0  0   0 0 0
```

```bash
ccdb add /epic/EcalBarrel/geometry  -r 0-         geometry.txt          "#from the survey of 2026"
ccdb add /epic/EcalBarrel/gains     -r 1-999      gains_2026a.txt       "#spring 2026 calibration"
ccdb add /epic/EcalBarrel/gains     -r 1000-1999  gains_2026b.txt       "#after the HV change"
ccdb add /epic/EcalBarrel/alignment -r 1-         alignment_nominal.txt "#nominal"
ccdb add /epic/EcalBarrel/alignment -r 1000-      alignment_2026b.txt   "#survey after the access of week 40"
```

Each `add` is a new version for a run range; the earlier versions stay. The production freezes what it reads
with a tag, and a later recalibration does not change what the tag gives:

```bash
ccdb tag pass1 -v default -t 2026-11-03-08-46-01 -c "first pass"      # the moment the campaign was frozen
ccdb add /epic/EcalBarrel/gains -r 1000-1999 gains_2026d.txt "#recalibrated after pass 1"
```

```
$ ccdb vers /epic/EcalBarrel/gains
(ID)     (created)              (user)           (variation)     (run range)      (comments)
 11      2026-11-03 08-46-03    calib            default         1000-1999       recalibrated after p
 8       2026-11-03 08-46-00    calib            default         1000-1999       after the HV change
 7       2026-11-03 08-45-59    calib            default         1-999           spring 2026 calibrat

$ ccdb cat /epic/EcalBarrel/gains:1500            # the newest for run 1500
| /world/EcalBarrel/module_1 | 1.14       | 5          |
| /world/EcalBarrel/module_2 | 1.27       | 7          |

$ ccdb cat /epic/EcalBarrel/gains:1500@pass1      # what the production sees: the version before the tag
| /world/EcalBarrel/module_1 | 1.12       | 5          |
| /world/EcalBarrel/module_2 | 1.25       | 7          |
```

### 3. The geometry reads `geometry` while the compact file is parsed

```xml
<lccdd>
  <properties>
    <plugin name="CCDB_Constants" type="xml" table="/epic/EcalBarrel/geometry" run="1" prefix="ecal_" tag="pass1"/>
  </properties>
  <detectors>
    <detector id="1" name="EcalBarrel" type="MyBarrelCalorimeter" material="ecal_material">
      <dimensions rmin="ecal_inner_radius" rmax="ecal_outer_radius" z="ecal_length" nsectors="ecal_n_sectors"/>
    </detector>
  </detectors>
</lccdd>
```

The plugin reads the row for run 1 under the tag, applies each column's own units (`105.5*mm`, `340*mm`;
`n_sectors` has none), and defines `ecal_inner_radius`, `ecal_outer_radius`, `ecal_length`, `ecal_n_sectors` and
`ecal_material` before the detectors are built, so the detector's XML uses them like any constant. The
connection string comes from `url=`, else `$CCDB_CONNECTION`, else `$JANA_CALIB_URL`.

### 4. The job reads `gains` and `alignment` as conditions for its run

```cpp
#include <CCDB_DD4hep.h>
#include <DD4hep/Detector.h>
#include <DD4hep/AlignmentsCalculator.h>
#include <DDCond/ConditionsManager.h>
#include <DDCond/ConditionsSlice.h>

dd4hep::Detector& detector = dd4hep::Detector::getInstance();
detector.fromXML("epic.xml");                                   // step 3 happens here

// the conditions manager with CCDB as its loader
detector.apply("DD4hep_ConditionsManagerInstaller", 0, nullptr);
auto manager = dd4hep::cond::ConditionsManager::from(detector);
manager["PoolType"]       = "DD4hep_ConditionsLinearPool";
manager["UserPoolType"]   = "DD4hep_ConditionsMapUserPool";
manager["UpdatePoolType"] = "DD4hep_ConditionsLinearUpdatePool";
manager["LoaderType"]     = "CCDB_ConditionsLoader";
manager.initialize();
manager.loader()["URL"] = std::string(getenv("CCDB_CONNECTION"));
manager.loader()["Tag"] = std::string("pass1");                 // the production's constants; or Variation and Time
const dd4hep::IOVType* runs = manager.registerIOVType(0, "run").second;

// which condition of which element comes from which table
auto content = std::make_shared<dd4hep::cond::ConditionsContent>();
dd4hep::DetElement ecal = detector.detector("EcalBarrel");
for (const auto& child : ecal.children()) {                      // /world/EcalBarrel/module_1, module_2, ...
    dd4hep::DetElement module = child.second;
    ccdb::dd4hep_plugins::AddCondition(*content, module, "gains",                       "/epic/EcalBarrel/gains");
    ccdb::dd4hep_plugins::AddCondition(*content, module, dd4hep::align::Keys::deltaName, "/epic/EcalBarrel/alignment");
}

// at each run change: prepare the slice, then read
void on_run(int run) {
    dd4hep::cond::ConditionsSlice slice(manager, content);
    manager.prepare(dd4hep::IOV(runs, run), slice);              // the loader is called for what the pools lack

    for (const auto& child : ecal.children()) {
        dd4hep::DetElement module = child.second;
        const auto& gains = slice.get(module, dd4hep::ConditionKey::itemCode("gains")).get<std::map<std::string, double>>();
        double gain = gains.at("gain"), pedestal = gains.at("pedestal");

        const dd4hep::Delta& delta = slice.get(module, dd4hep::align::Keys::deltaKey).get<dd4hep::Delta>();
        // ...
    }

    // alignment: the deltas become aligned transformations, as DDAlign does it
    std::map<dd4hep::DetElement, dd4hep::Delta> deltas;
    for (const auto& child : ecal.children())
        deltas[child.second] = slice.get(child.second, dd4hep::align::Keys::deltaKey).get<dd4hep::Delta>();
    dd4hep::align::AlignmentsCalculator().compute(deltas, slice);
    dd4hep::Alignment aligned = slice.get(ecal.child("module_1"), dd4hep::align::Keys::alignmentKey);
    const double* position = aligned.worldTransformation().GetTranslation();   // nominal + (1.0 mm, 0, -3.0 mm) for run >= 1000
}
```

What the job sees, from the data of step 2: for run 500, `module_1` gain 1.10 and the nominal alignment; for
run 1500 under `pass1`, gain 1.12 and the week-40 survey (`dx` 1.0 mm, `dz` −3.0 mm, `dpsi` 0.01 rad); without
the tag, the newest, gain 1.14. The loader resolves each table once per run with the C++ library (the same
resolution as `ccdb cat`, with the variation's parents and the tag's time), picks the row whose `element` is the
module's path, and returns the conditions with the run as their interval of validity.

### What to decide for a real detector

- **The key column.** The loader matches `element` against the element's full DD4hep path. A short name or
  the element's id would be a one-line change in the loader; settle it with the first real table.
- **Which tables are conditions.** Only what DD4hep asks per element needs the `element` column; numbers the
  geometry needs are a one-row table for `CCDB_Constants`; what reconstruction reads per event goes through the
  [JANA2 service](apis/jana.md) as before.
- **Large payloads.** A condition is a row of numbers and text. A field map or a model file is a resources
  row (URL, SHA-256, size), fetched and checked by the JANA2 service.

## Simulation

Simulation reads geometry and conditions like reconstruction does: give the simulation the run numbers of
the period it simulates, read the `mc` variation (`variation="mc"`, `Variation`), and fix the constants of a
production with a tag (`tag=`, `Tag`), so a production can be repeated. See
[Streaming readout and runs](concepts/streaming-readout.md#simulation).
