// SPDX-License-Identifier: LGPL-3.0-or-later
//
// CCDB and DD4hep, end to end (docs/apis/dd4hep-tutorial.md): a two-module calorimeter whose dimensions come from a
// CCDB table while the compact file is read, and whose gains and alignment come from CCDB tables as DD4hep
// conditions for the run of a job.
//
//   ccdb_dd4hep_example <compact.xml> <run> [tag]
//
// The compact file carries the CCDB_Constants plugin (see the tutorial); the connection string comes from
// CCDB_CONNECTION. The program prints what the geometry got, and for the run what each module's conditions are and
// where the module sits once its alignment delta is applied. scripts/eic/dd4hep_example.sh builds the database,
// runs this for two runs and a tag, and checks the printed values.
#include <CCDB_DD4hep.h>

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
#include <DDCond/ConditionsManager.h>
#include <DDCond/ConditionsSlice.h>

#include <cstdio>
#include <cstdlib>
#include <map>
#include <memory>
#include <string>

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::fprintf(stderr, "usage: %s <compact.xml> <run> [tag]   (CCDB_CONNECTION names the database)\n", argv[0]);
        return 2;
    }
    const std::string compact = argv[1];
    const int run = std::atoi(argv[2]);
    const std::string tag = argc > 3 ? argv[3] : "";
    dd4hep::setPrintLevel(dd4hep::WARNING);

    // 1. Geometry. Reading the compact file runs CCDB_Constants, which defines ecal_* constants from the table
    //    /epic/EcalBarrel/geometry before any detector is built. A real detector plugin reads them the same way.
    auto& detector = dd4hep::Detector::getInstance();
    detector.fromXML(compact);
    const double inner = detector.constant<double>("ecal_inner_radius");
    const double outer = detector.constant<double>("ecal_outer_radius");
    const double length = detector.constant<double>("ecal_length");
    const int sectors = detector.constant<int>("ecal_n_sectors");
    const std::string material = detector.constantAsString("ecal_material");
    std::printf("geometry: inner_radius=%g mm outer_radius=%g mm length=%g mm n_sectors=%d material=%s\n",
                inner / dd4hep::mm, outer / dd4hep::mm, length / dd4hep::mm, sectors, material.c_str());

    // The barrel: an envelope tube from the inner to the outer radius, and two modules inside it on the x axis
    // (a stand-in for a detector constructor, which would use the same constants)
    dd4hep::DetElement ecal(detector.world(), "EcalBarrel", 1);
    dd4hep::Volume envelope("EcalBarrel_envelope", dd4hep::Tube(inner, outer, length / 2), detector.air());
    ecal.setPlacement(detector.worldVolume().placeVolume(envelope));
    dd4hep::Volume module_volume("module", dd4hep::Box((outer - inner) / 2, 10 * dd4hep::cm, length / 2), detector.material(material));
    std::map<int, dd4hep::DetElement> modules;
    for (int number : {1, 2}) {
        double x = (number == 1 ? 1 : -1) * (inner + (outer - inner) / 2);              // the middle of the crystal
        dd4hep::PlacedVolume placed = envelope.placeVolume(module_volume, dd4hep::Position(x, 0, 0));
        modules[number] = dd4hep::DetElement(ecal, "module_" + std::to_string(number), number);
        modules[number].setPlacement(placed);
    }
    detector.endDocument();                                   // the compact file left the geometry open for this

    // 2. Conditions. The manager's loader is CCDB; the content says which table holds which condition of which module.
    detector.apply("DD4hep_ConditionsManagerInstaller", 0, nullptr);
    dd4hep::cond::ConditionsManager manager = dd4hep::cond::ConditionsManager::from(detector);
    manager["PoolType"] = "DD4hep_ConditionsLinearPool";
    manager["UserPoolType"] = "DD4hep_ConditionsMapUserPool";
    manager["UpdatePoolType"] = "DD4hep_ConditionsLinearUpdatePool";
    manager["LoaderType"] = "CCDB_ConditionsLoader";
    manager.initialize();
    manager.loader()["URL"] = std::string(std::getenv("CCDB_CONNECTION") ? std::getenv("CCDB_CONNECTION") : "");
    if (!tag.empty()) manager.loader()["Tag"] = tag;            // the production's constants; else the newest
    const dd4hep::IOVType* runs = manager.registerIOVType(0, "run").second;

    auto content = std::make_shared<dd4hep::cond::ConditionsContent>();
    for (auto& entry : modules) {
        ccdb::dd4hep_plugins::AddCondition(*content, entry.second, "gains", "/epic/EcalBarrel/gains");
        ccdb::dd4hep_plugins::AddCondition(*content, entry.second, dd4hep::align::Keys::deltaName, "/epic/EcalBarrel/alignment");
    }

    // 3. One run: prepare the slice (CCDB is asked once per table), read the conditions, apply the alignment
    dd4hep::cond::ConditionsSlice slice(manager, content);
    dd4hep::cond::ConditionsManager::Result result = manager.prepare(dd4hep::IOV(runs, run), slice);
    if (result.missing) {
        std::fprintf(stderr, "run %d: %zu conditions missing\n", run, result.missing);
        return 1;
    }
    std::map<dd4hep::DetElement, dd4hep::Delta> deltas;
    for (auto& entry : modules) {
        deltas[entry.second] = slice.get(entry.second, dd4hep::align::Keys::deltaKey).get<dd4hep::Delta>();
    }
    dd4hep::align::AlignmentsCalculator().compute(deltas, slice);

    std::printf("run %d%s:\n", run, tag.empty() ? "" : (" tag " + tag).c_str());
    for (auto& entry : modules) {
        dd4hep::DetElement module = entry.second;
        const auto& gains = slice.get(module, dd4hep::ConditionKey::itemCode("gains")).get<std::map<std::string, double>>();
        const dd4hep::Delta& delta = deltas[module];
        dd4hep::Alignment aligned = slice.get(module, dd4hep::align::Keys::alignmentKey);
        const double* position = aligned.worldTransformation().GetTranslation();
        std::printf("  %-28s gain=%g pedestal=%g ADC  delta dx=%g dz=%g mm dpsi=%g rad  aligned x=%g z=%g mm\n",
                    module.path().c_str(), gains.at("gain"), gains.at("pedestal"),
                    delta.translation.X() / dd4hep::mm, delta.translation.Z() / dd4hep::mm, delta.rotation.Psi(),
                    position[0] / dd4hep::mm, position[2] / dd4hep::mm);
    }
    return 0;
}
