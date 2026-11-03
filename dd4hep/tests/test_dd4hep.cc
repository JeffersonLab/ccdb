// The DD4hep plugins of CCDB (dd4hep/src) against the database of scripts/eic/make_dd4hep_test_db.py:
//   CCDB_TEST_DD4HEP_SQLITE   the file the script made
//   DD4hepINSTALL             DD4hep's installation, for its element and material tables (eic-shell sets it)
// This program links DD4hep only, not libccdb_dd4hep: the plugins load through DD4hep's plugin manager, so
// LD_LIBRARY_PATH must hold libccdb_dd4hep and its .components file; scripts/eic/dd4hep_tests.sh sets both and runs this.
#define CATCH_CONFIG_MAIN
#include "tests/catch.hpp"

#include "CCDB_DD4hep.h"

#include <DD4hep/AlignmentData.h>
#include <DD4hep/Alignments.h>
#include <DD4hep/AlignmentsCalculator.h>
#include <DD4hep/Conditions.h>
#include <DD4hep/Detector.h>
#include <DD4hep/DetElement.h>
#include <DD4hep/Printout.h>
#include <DD4hep/Shapes.h>
#include <DD4hep/Volumes.h>
#include <DDCond/ConditionsContent.h>
#include <DDCond/ConditionsDataLoader.h>
#include <DDCond/ConditionsManager.h>
#include <DDCond/ConditionsSlice.h>

#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>

using namespace std;

namespace {

    string Setting(const char* name) {
        const char* value = getenv(name);
        if (!value) throw runtime_error(string(name) + " is not set: run scripts/eic/dd4hep_tests.sh");
        return value;
    }

    string Connection() { return "sqlite:///" + Setting("CCDB_TEST_DD4HEP_SQLITE"); }

    /// A compact file: DD4hep's elements and materials, a 10 m world, and `properties` (plugins) if given; with
    /// keepOpen the reader leaves the document open, so the test can add volumes and close it with endDocument()
    string Compact(const string& name, const string& properties, bool keepOpen = false) {
        string install = Setting("DD4hepINSTALL");
        string path = string(getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp") + "/ccdb_dd4hep_" + name + ".xml";
        ofstream out(path);
        out << "<lccdd>\n" << (keepOpen ? "  <geometry open=\"true\" close=\"false\"/>\n" : "") <<
               "  <includes>\n"
               "    <gdmlFile ref=\"" << install << "/DDDetectors/compact/elements.xml\"/>\n"
               "    <gdmlFile ref=\"" << install << "/DDDetectors/compact/materials.xml\"/>\n"
               "  </includes>\n"
               "  <define>\n"
               "    <constant name=\"world_side\" value=\"10*m\"/>\n"
               "    <constant name=\"world_x\" value=\"world_side\"/>\n"
               "    <constant name=\"world_y\" value=\"world_side\"/>\n"
               "    <constant name=\"world_z\" value=\"world_side\"/>\n"
               "  </define>\n"
               "  <properties>\n" << properties << "  </properties>\n"
               "</lccdd>\n";
        return path;
    }
}


TEST_CASE("CCDB_Constants/compact constants from a one-row table", "[dd4hep]")
{
    dd4hep::setPrintLevel(dd4hep::WARNING);
    auto detector = dd4hep::Detector::make_unique("ccdb_constants");
    detector->fromXML(Compact("constants",
        "    <plugin name=\"CCDB_Constants\" type=\"xml\" url=\"" + Connection() + "\" table=\"/test/dd4hep/ecal_dims\"\n"
        "            run=\"1\" prefix=\"ecal_\" units=\"mm\">\n"
        "      <unit column=\"n_sectors\" value=\"\"/>\n"
        "    </plugin>\n"));

    REQUIRE(detector->constant<double>("ecal_inner_radius") == Approx(105.5 * dd4hep::mm));
    REQUIRE(detector->constant<double>("ecal_outer_radius") == Approx(16.0 * dd4hep::cm));
    REQUIRE(detector->constant<double>("ecal_length") == Approx(0.34 * dd4hep::m));
    REQUIRE(detector->constant<int>("ecal_n_sectors") == 48);
    REQUIRE(detector->constantAsString("ecal_material") == "PbWO4");
    // the constants are in the compact evaluator: detector descriptions can use them in expressions
    REQUIRE(dd4hep::_toDouble("ecal_outer_radius - ecal_inner_radius") == Approx(54.5 * dd4hep::mm));
}


TEST_CASE("CCDB_Constants/errors", "[dd4hep]")
{
    dd4hep::setPrintLevel(dd4hep::FATAL);
    auto detector = dd4hep::Detector::make_unique("ccdb_constants_errors");
    // gains has two rows: not a table of constants
    REQUIRE_THROWS(detector->fromXML(Compact("constants_two_rows",
        "    <plugin name=\"CCDB_Constants\" type=\"xml\" url=\"" + Connection() + "\" table=\"/test/dd4hep/gains\" run=\"1\"/>\n")));
}


TEST_CASE("CCDB_ConditionsLoader/conditions and alignment deltas for two runs", "[dd4hep]")
{
    dd4hep::setPrintLevel(dd4hep::WARNING);
    auto detector = dd4hep::Detector::make_unique("ccdb_conditions");
    detector->fromXML(Compact("conditions", "", true));

    // Two boxes, /world/box1 at x = 50 cm and /world/box2 at x = 100 cm
    dd4hep::Volume box("box", dd4hep::Box(10 * dd4hep::cm, 10 * dd4hep::cm, 10 * dd4hep::cm), detector->air());
    dd4hep::DetElement world = detector->world();
    map<int, dd4hep::DetElement> boxes;
    for (int number : {1, 2}) {
        dd4hep::PlacedVolume placed = detector->worldVolume().placeVolume(box, dd4hep::Position(number * 50 * dd4hep::cm, 0, 0));
        boxes[number] = dd4hep::DetElement(world, "box" + to_string(number), number);
        boxes[number].setPlacement(placed);
    }
    detector->endDocument();
    REQUIRE(boxes[1].path() == "/world/box1");

    detector->apply("DD4hep_ConditionsManagerInstaller", 0, nullptr);
    dd4hep::cond::ConditionsManager manager = dd4hep::cond::ConditionsManager::from(*detector);
    manager["PoolType"] = "DD4hep_ConditionsLinearPool";
    manager["UserPoolType"] = "DD4hep_ConditionsMapUserPool";
    manager["UpdatePoolType"] = "DD4hep_ConditionsLinearUpdatePool";
    manager["LoaderType"] = "CCDB_ConditionsLoader";
    manager.initialize();
    manager.loader()["URL"] = Connection();
    const dd4hep::IOVType* runs = manager.registerIOVType(0, "run").second;
    REQUIRE(runs != nullptr);

    auto content = make_shared<dd4hep::cond::ConditionsContent>();
    using ccdb::dd4hep_plugins::AddCondition;
    AddCondition(*content, boxes[1], "gains", "/test/dd4hep/gains");
    AddCondition(*content, boxes[2], "gains", "/test/dd4hep/gains");
    AddCondition(*content, boxes[1], dd4hep::align::Keys::deltaName, "/test/dd4hep/alignment");

    struct Expected { int run; double gain1, gain2, pedestal2, dx, dz; };
    for (const Expected& expected : {Expected{50, 1.10, 1.20, 6, 1, 0}, Expected{150, 2.10, 2.20, 16, 2, -3}}) {
        INFO("run " << expected.run);
        dd4hep::cond::ConditionsSlice slice(manager, content);
        dd4hep::cond::ConditionsManager::Result result = manager.prepare(dd4hep::IOV(runs, expected.run), slice);
        REQUIRE(result.missing == 0);
        REQUIRE(result.loaded == 3);

        dd4hep::Condition gains1 = slice.get(boxes[1], dd4hep::ConditionKey::itemCode("gains"));
        dd4hep::Condition gains2 = slice.get(boxes[2], dd4hep::ConditionKey::itemCode("gains"));
        REQUIRE(gains1.isValid());
        REQUIRE(gains1.get<map<string, double>>().at("gain") == Approx(expected.gain1));
        REQUIRE(gains2.get<map<string, double>>().at("gain") == Approx(expected.gain2));
        REQUIRE(gains2.get<map<string, double>>().at("pedestal") == Approx(expected.pedestal2));
        REQUIRE(gains1.get<map<string, double>>().count("element") == 0);      // the text column is the key, not a value
        REQUIRE(gains1.iov().keyData.first == expected.run);
        REQUIRE(gains1.iov().keyData.second == expected.run);

        dd4hep::Condition deltaCondition = slice.get(boxes[1], dd4hep::align::Keys::deltaKey);
        REQUIRE(deltaCondition.isValid());
        const dd4hep::Delta& delta = deltaCondition.get<dd4hep::Delta>();
        REQUIRE(delta.translation.X() == Approx(expected.dx * dd4hep::mm));
        REQUIRE(delta.translation.Z() == Approx(expected.dz * dd4hep::mm).margin(1e-12));

        // DDAlign applies the delta: box1's world position moves by it
        map<dd4hep::DetElement, dd4hep::Delta> deltas{{boxes[1], delta}};
        dd4hep::align::AlignmentsCalculator calculator;
        dd4hep::align::AlignmentsCalculator::Result aligned = calculator.compute(deltas, slice);
        REQUIRE(aligned.missing == 0);
        dd4hep::Alignment alignment = slice.get(boxes[1], dd4hep::align::Keys::alignmentKey);
        REQUIRE(alignment.isValid());
        const double* position = alignment.worldTransformation().GetTranslation();
        REQUIRE(position[0] == Approx(50 * dd4hep::cm + expected.dx * dd4hep::mm));
        REQUIRE(position[2] == Approx(expected.dz * dd4hep::mm).margin(1e-12));
    }
}
