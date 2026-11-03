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

## Simulation

Simulation reads geometry and conditions like reconstruction does: give the simulation the run numbers of
the period it simulates, read the `mc` variation (`variation="mc"`, `Variation`), and fix the constants of a
production with a tag (`tag=`, `Tag`), so a production can be repeated. See
[Streaming readout and runs](concepts/streaming-readout.md#simulation).
