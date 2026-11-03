// SPDX-License-Identifier: LGPL-3.0-or-later
// CCDB_ConditionsLoader: a DDCond conditions loader that reads detector element conditions from CCDB (docs/apis/dd4hep.md).
//
//   manager["LoaderType"] = "CCDB_ConditionsLoader";      // before manager.initialize()
//   manager.initialize();
//   manager.loader()["URL"] = std::string("sqlite:////path/ccdb.sqlite");   // or $CCDB_CONNECTION, $JANA_CALIB_URL
//   ccdb::dd4hep_plugins::AddCondition(*content, element, dd4hep::align::Keys::deltaName, "/epic/alignment/ecal");
//   manager.prepare(dd4hep::IOV(run_type, run), *slice);    // loads what the slice misses for that run
//
// A condition comes from the row of its table whose column `element` holds the detector element's path. The item
// dd4hep::align::Keys::deltaName gives a dd4hep::Delta from the columns dx, dy, dz (LengthUnit, default mm) and
// dphi, dtheta, dpsi (AngleUnit, default rad), flagged as an alignment delta for DDAlign; any other item gives a
// std::map<std::string, double> of the row's numeric columns. The IOV of a loaded condition is the requested run: the
// C++ library does not report an assignment's run range, so the next run loads again (from the Calibration of that
// run, which the loader keeps). Properties: URL, Variation (default "default"), Time (UTC or local text; default the
// newest) or Tag, LengthUnit, AngleUnit.
#include <DD4hep/AlignmentData.h>
#include <DD4hep/Alignments.h>
#include <DD4hep/Factories.h>
#include <DD4hep/Printout.h>
#include <DDCond/ConditionsDataLoader.h>
#include <DDCond/ConditionsManager.h>
#include <DDCond/ConditionsPool.h>

#include <CCDB/CalibrationGenerator.h>
#include <CCDB/Helpers/TimeUtils.h>

#include <cstdlib>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

    using dd4hep::cond::ConditionsDataLoader;
    using dd4hep::cond::ConditionsManager;
    using dd4hep::cond::ConditionsManagerObject;

    class CCDBConditionsLoader : public ConditionsDataLoader {
    public:
        CCDBConditionsLoader(dd4hep::Detector& description, ConditionsManager manager, const std::string& name)
            : ConditionsDataLoader(description, manager, name) {
            declareProperty("URL", m_url);
            declareProperty("Variation", m_variation);
            declareProperty("Time", m_time);
            declareProperty("Tag", m_tag);
            declareProperty("LengthUnit", m_lengthUnit);
            declareProperty("AngleUnit", m_angleUnit);
        }

        ~CCDBConditionsLoader() override { m_generator.DeleteCalibrations(); }

        size_t load_many(const dd4hep::IOV& requested, RequiredItems& work, LoadedItems& loaded, dd4hep::IOV& validity) override;

    private:
        ccdb::Calibration* CalibrationOf(int run);
        const std::vector<std::map<std::string, std::string>>& Rows(ccdb::Calibration* calib, const std::string& table);

        std::string m_url;
        std::string m_variation = "default";
        std::string m_time;
        std::string m_tag;
        std::string m_lengthUnit = "mm";
        std::string m_angleUnit = "rad";
        ccdb::CalibrationGenerator m_generator;
        std::map<std::pair<ccdb::Calibration*, std::string>, std::vector<std::map<std::string, std::string>>> m_rows;
    };


    ccdb::Calibration* CCDBConditionsLoader::CalibrationOf(int run) {
        std::string url = m_url;
        if (url.empty() && std::getenv("CCDB_CONNECTION")) url = std::getenv("CCDB_CONNECTION");
        if (url.empty() && std::getenv("JANA_CALIB_URL")) url = std::getenv("JANA_CALIB_URL");
        if (url.empty()) throw std::runtime_error("CCDB_ConditionsLoader: no URL property, and neither CCDB_CONNECTION nor JANA_CALIB_URL is set");
        if (!m_tag.empty()) return m_generator.MakeCalibrationForTag(url, run, m_tag);
        int64_t time = 0;
        if (!m_time.empty()) {
            bool parsed = false;
            time = ccdb::TimeUtils::ParseLocalTime(m_time, &parsed);
            if (!parsed) throw std::runtime_error("CCDB_ConditionsLoader: can't read Time='" + m_time + "'");
        }
        return m_generator.MakeCalibrationMicro(url, run, m_variation, time);
    }


    const std::vector<std::map<std::string, std::string>>& CCDBConditionsLoader::Rows(ccdb::Calibration* calib, const std::string& table) {
        auto key = std::make_pair(calib, table);
        auto found = m_rows.find(key);
        if (found != m_rows.end()) return found->second;
        std::vector<std::map<std::string, std::string>> rows;
        calib->GetCalib(rows, table);          // throws when the table does not resolve for the run
        return m_rows.emplace(key, std::move(rows)).first->second;
    }


    double Number(const std::map<std::string, std::string>& row, const char* column) {
        auto cell = row.find(column);
        return cell == row.end() ? 0.0 : std::strtod(cell->second.c_str(), nullptr);
    }


    size_t CCDBConditionsLoader::load_many(const dd4hep::IOV& requested, RequiredItems& work, LoadedItems& loaded, dd4hep::IOV& validity) {
        size_t before = loaded.size();
        int run = static_cast<int>(requested.keyData.first);
        ccdb::Calibration* calib = CalibrationOf(run);
        dd4hep::IOV iov(requested.iovType, dd4hep::IOV::Key(run, run));
        dd4hep::cond::ConditionsPool* pool = m_mgr.registerIOV(*iov.iovType, iov.key());
        double lengthUnit = dd4hep::_toDouble(m_lengthUnit);
        double angleUnit = dd4hep::_toDouble(m_angleUnit);

        for (const auto& item : work) {
            const std::string* address = item.second ? item.second->data<std::string>() : nullptr;
            if (!address) continue;                     // not one of ours: no load information
            size_t hash = address->find('#');
            if (hash == std::string::npos) continue;
            std::string table = address->substr(0, hash), element = address->substr(hash + 1);

            const std::map<std::string, std::string>* row = nullptr;
            for (const auto& candidate : Rows(calib, table)) {
                auto cell = candidate.find("element");
                if (cell != candidate.end() && cell->second == element) { row = &candidate; break; }
            }
            if (!row) {
                dd4hep::printout(dd4hep::ERROR, "CCDB_ConditionsLoader", "%s for run %d has no row for %s", table.c_str(), run, element.c_str());
                continue;
            }

            dd4hep::ConditionKey::KeyMaker key(item.first);
            dd4hep::Condition condition(*address, "ccdb");
            condition->hash = item.first;
            if (key.values.item_key == dd4hep::align::Keys::deltaKey) {
                dd4hep::Delta& delta = condition.bind<dd4hep::Delta>();
                delta.translation = dd4hep::Position(Number(*row, "dx") * lengthUnit, Number(*row, "dy") * lengthUnit, Number(*row, "dz") * lengthUnit);
                delta.rotation = dd4hep::RotationZYX(Number(*row, "dphi") * angleUnit, Number(*row, "dtheta") * angleUnit, Number(*row, "dpsi") * angleUnit);
                delta.flags |= dd4hep::Delta::HAVE_TRANSLATION | dd4hep::Delta::HAVE_ROTATION;
                condition->setFlag(dd4hep::Condition::ACTIVE | dd4hep::Condition::ALIGNMENT_DELTA);
            } else {
                auto& values = condition.bind<std::map<std::string, double>>();
                for (const auto& cell : *row) {
                    char* end = nullptr;
                    double value = std::strtod(cell.second.c_str(), &end);
                    if (!cell.second.empty() && end && *end == '\0') values[cell.first] = value;
                }
                condition->setFlag(dd4hep::Condition::ACTIVE);
            }
            if (!m_mgr.registerUnlocked(*pool, condition)) {
                dd4hep::printout(dd4hep::WARNING, "CCDB_ConditionsLoader", "could not register %s", address->c_str());
                continue;
            }
            loaded[item.first] = condition;
        }
        if (loaded.size() > before) validity.iov_intersection(iov.key());
        dd4hep::printout(dd4hep::DEBUG, "CCDB_ConditionsLoader", "run %d: %zu of %zu conditions", run, loaded.size() - before, work.size());
        return loaded.size() - before;
    }


    void* CreateLoader(dd4hep::Detector& description, int argc, char** argv) {
        const char* name = argc > 0 ? argv[0] : "CCDB_ConditionsLoader";
        ConditionsManagerObject* manager = reinterpret_cast<ConditionsManagerObject*>(argc > 1 ? argv[1] : nullptr);
        return new CCDBConditionsLoader(description, ConditionsManager(manager), name);
    }
}

DECLARE_DD4HEP_CONSTRUCTOR(CCDB_ConditionsLoader, CreateLoader)
