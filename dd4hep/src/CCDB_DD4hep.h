// CCDB in DD4hep (docs/apis/dd4hep.md): two plugins in the library ccdb_dd4hep.
//
//   CCDB_Constants         compact XML constants from a one-row CCDB table, at parse time:
//                            <properties>
//                              <plugin name="CCDB_Constants" type="xml" table="/epic/geometry/ecal_dims" run="1"
//                                      prefix="ecal_" units="mm"/>
//                            </properties>
//   CCDB_ConditionsLoader  a DDCond conditions loader: conditions of detector elements from CCDB tables, one row per
//                          element, for the run of the requested IOV; alignment deltas become dd4hep::Delta
//
// AddCondition below tells a ConditionsContent which table holds a detector element's condition. It is inline: a
// program includes this header and links nothing of CCDB; DD4hep's plugin manager loads libccdb_dd4hep through its
// .components file on LD_LIBRARY_PATH (dd4hep_tests.sh and the tests work this way).
#ifndef CCDB_DD4HEP_H
#define CCDB_DD4HEP_H

#include <DD4hep/Conditions.h>
#include <DD4hep/DetElement.h>
#include <DDCond/ConditionsContent.h>
#include <DDCond/ConditionsDataLoader.h>      // the loader's properties: manager.loader()["URL"] (ConditionsManager.h only declares the class)

#include <string>

namespace ccdb {
namespace dd4hep_plugins {

    /// The load address of a condition: the table and the element's path, "table#/world/element"
    inline std::string ConditionAddress(const std::string& table, dd4hep::DetElement element) {
        return table + "#" + element.path();
    }

    /** @brief Adds the condition `item` of `element` to `content`: CCDB_ConditionsLoader reads it from `table`, the row
     *  whose column `element` holds the element's path. The item dd4hep::align::Keys::deltaName makes an alignment delta
     *  (columns dx, dy, dz, dphi, dtheta, dpsi); any other item a std::map<std::string, double> of the numeric columns.
     *  @return the condition key */
    inline dd4hep::Condition::key_type AddCondition(dd4hep::cond::ConditionsContent& content, dd4hep::DetElement element,
                                                    const std::string& item, const std::string& table) {
        return content.addLocation(element, dd4hep::ConditionKey::itemCode(item), ConditionAddress(table, element)).first;
    }
}
}

#endif // CCDB_DD4HEP_H
