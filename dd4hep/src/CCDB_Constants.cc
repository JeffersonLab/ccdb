// SPDX-License-Identifier: LGPL-3.0-or-later
// CCDB_Constants: compact XML constants from a one-row CCDB table (docs/apis/dd4hep.md).
//
//   <properties>
//     <plugin name="CCDB_Constants" type="xml" table="/epic/geometry/ecal_dims" run="1" prefix="ecal_" units="mm">
//       <unit column="n_sectors" value=""/>
//     </plugin>
//   </properties>
//
// One constant per column, named prefix + column: numbers as "(value)*units", so the compact evaluator converts them
// to DD4hep's units; strings as string constants. The compact reader runs <properties> plugins before the detectors,
// so detector descriptions can use the constants. Attributes: table (required), run (default 0), url (default
// $CCDB_CONNECTION, then $JANA_CALIB_URL), variation (default "default"), time (UTC or local text, as ccdb:time of the
// JANA2 service; default the newest) or tag, prefix (default none), units (for every number column) and
// <unit column= value=/> children for single columns. Without them a column's own units (schema 6, `mktbl
// name=double:mm`) apply; a <unit> child wins over `units`, which wins over the column's.
#include <DD4hep/DetFactoryHelper.h>
#include <DD4hep/Printout.h>
#include <XML/Utilities.h>

#include <CCDB/CalibrationGenerator.h>
#include <CCDB/Model/Assignment.h>
#include <CCDB/Model/ConstantsTypeColumn.h>
#include <CCDB/Model/ConstantsTypeTable.h>
#include <CCDB/Helpers/TimeUtils.h>

#include <cstdlib>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>

namespace {

    std::string Attribute(xml_h element, const char* name, const std::string& fallback = "") {
        xml_attr_t attribute = element.attr_nothrow(dd4hep::xml::Strng_t(name));
        return attribute ? element.attr<std::string>(attribute) : fallback;
    }

    bool IsNumber(const std::string& text) {
        if (text.empty()) return false;
        char* end = nullptr;
        std::strtod(text.c_str(), &end);
        return end != nullptr && *end == '\0';
    }

    std::string Connection(xml_h element) {
        std::string url = Attribute(element, "url");
        if (url.empty() && std::getenv("CCDB_CONNECTION")) url = std::getenv("CCDB_CONNECTION");
        if (url.empty() && std::getenv("JANA_CALIB_URL")) url = std::getenv("JANA_CALIB_URL");
        if (url.empty()) throw std::runtime_error("CCDB_Constants: no url attribute, and neither CCDB_CONNECTION nor JANA_CALIB_URL is set");
        return url;
    }

    long CreateConstants(dd4hep::Detector& description, xml_h element) {
        std::string table = Attribute(element, "table");
        if (table.empty()) throw std::runtime_error("CCDB_Constants: the table attribute is required");
        std::string url = Connection(element);
        int run = std::atoi(Attribute(element, "run", "0").c_str());
        std::string variation = Attribute(element, "variation", "default");
        std::string tag = Attribute(element, "tag");
        std::string timeText = Attribute(element, "time");
        std::string prefix = Attribute(element, "prefix");
        std::string units = Attribute(element, "units");
        std::map<std::string, std::string> columnUnits;
        for (xml_coll_t unit(element, dd4hep::xml::Strng_t("unit")); unit; ++unit) {
            columnUnits[unit.attr<std::string>(dd4hep::xml::Strng_t("column"))] = unit.attr<std::string>(dd4hep::xml::Strng_t("value"));
        }

        int64_t timeMicro = 0;
        if (!timeText.empty()) {
            bool parsed = false;
            timeMicro = ccdb::TimeUtils::ParseLocalTime(timeText, &parsed);
            if (!parsed) throw std::runtime_error("CCDB_Constants: can't read time='" + timeText + "'");
        }
        ccdb::CalibrationGenerator generator;
        ccdb::Calibration* calib = tag.empty() ? generator.MakeCalibrationMicro(url, run, variation, timeMicro)
                                               : generator.MakeCalibrationForTag(url, run, tag);
        std::vector<std::map<std::string, std::string>> rows;
        if (!calib->GetCalib(rows, table) || rows.size() != 1) {
            throw std::runtime_error("CCDB_Constants: " + table + " for run " + std::to_string(run) + " must hold one row, it holds " +
                                     std::to_string(rows.size()));
        }
        // the columns' own units (schema 6), used where the XML names none
        std::map<std::string, std::string> storedUnits;
        if (ccdb::Assignment* assignment = calib->GetAssignment(table)) {
            for (ccdb::ConstantsTypeColumn* column : assignment->GetTypeTable()->GetColumns()) {
                storedUnits[column->GetName()] = column->GetUnits();
            }
        }
        for (const auto& cell : rows[0]) {
            std::string name = prefix + cell.first;
            auto unit = columnUnits.find(cell.first);
            std::string unitText = unit != columnUnits.end() ? unit->second : (!units.empty() ? units : storedUnits[cell.first]);
            if (IsNumber(cell.second)) {
                std::string value = unitText.empty() ? cell.second : "(" + cell.second + ")*" + unitText;
                description.addConstant(dd4hep::Constant(name, value, "number"));
                dd4hep::_toDictionary(name, value, "number");
            } else {
                description.addConstant(dd4hep::Constant(name, cell.second, "string"));
                dd4hep::_toDictionary(name, cell.second, "string");
            }
            dd4hep::printout(dd4hep::DEBUG, "CCDB_Constants", "%s = %s", name.c_str(), cell.second.c_str());
        }
        dd4hep::printout(dd4hep::INFO, "CCDB_Constants", "%zu constants from %s, run %d%s", rows[0].size(), table.c_str(), run,
                         tag.empty() ? "" : (", tag " + tag).c_str());
        generator.DeleteCalibrations();
        return 1;
    }
}

DECLARE_XML_PLUGIN(CCDB_Constants, CreateConstants)
