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

## Worked example

[CCDB and DD4hep, step by step](apis/dd4hep-tutorial.md) builds a two-module calorimeter whose geometry numbers,
gains and alignment live in CCDB: the tables and the `ccdb` commands that fill them, a tag and a recalibration
after it, the compact file, the job (`dd4hep/examples/ccdb_dd4hep_example.cc`) and its output for two runs and
the tag, every command run by CI as written.

## Simulation

Simulation reads geometry and conditions like reconstruction does: give the simulation the run numbers of
the period it simulates, read the `mc` variation (`variation="mc"`, `Variation`), and fix the constants of a
production with a tag (`tag=`, `Tag`), so a production can be repeated. See
[Streaming readout and runs](concepts/streaming-readout.md#simulation).
