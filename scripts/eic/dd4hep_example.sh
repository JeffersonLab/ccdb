#!/usr/bin/env bash
# The CCDB and DD4hep tutorial (docs/apis/dd4hep-tutorial.md), run end to end inside eic-shell:
#
#   scripts/eic/run_in_eic_shell.sh scripts/eic/dd4hep_example.sh
#
# It builds the library with the DD4hep plugins and the example program, creates a SQLite database with the `ccdb`
# commands the page shows, writes the page's compact file, runs ccdb_dd4hep_example for run 500, run 1500 and run
# 1500 under the tag pass1, prints the output, and checks the values. CCDB_DD4HEP_BUILD_DIR sets the build tree.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
build="${CCDB_DD4HEP_BUILD_DIR:-$repo/build/dd4hep}"
jobs="$(( $(nproc) > 4 ? $(nproc) - 2 : $(nproc) ))"
work="$build/tutorial"
mkdir -p "$work"

cmake -S "$repo/cpp" -B "$build" -DCCDB_BUILD_DD4HEP=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo > /dev/null
cmake --build "$build" --target ccdb_dd4hep Components_ccdb_dd4hep ccdb_dd4hep_example -j "$jobs" > /dev/null

# --- the data, with the ccdb command line (the checkout's package; installed, `ccdb` alone does the same)
export CCDB_CONNECTION="sqlite:///$work/ccdb.sqlite"
rm -f "$work/ccdb.sqlite"
ccdb() { PYTHONPATH="$repo/python" python3 -m ccdb -u calib "$@"; }
ccdb db init --init-i-am-sure > /dev/null
ccdb user --create calib > /dev/null

ccdb mkdir /epic "#ePIC" > /dev/null
ccdb mkdir /epic/EcalBarrel "#Barrel ECal" > /dev/null
ccdb mktbl /epic/EcalBarrel/geometry  -r 1 inner_radius=double:mm outer_radius=double:mm length=double:mm n_sectors=int material=string "#Barrel ECal envelope" > /dev/null
ccdb mktbl /epic/EcalBarrel/gains     -r 2 element=string gain=double pedestal=double:ADC "#Barrel ECal gain and pedestal per module" > /dev/null
ccdb mktbl /epic/EcalBarrel/alignment -r 2 element=string dx=double:mm dy=double:mm dz=double:mm dphi=double:rad dtheta=double:rad dpsi=double:rad "#Barrel ECal module alignment" > /dev/null

cd "$work"
printf '105.5 160 340 48 PbWO4\n' > geometry.txt
printf '/world/EcalBarrel/module_1 1.10 5\n/world/EcalBarrel/module_2 1.20 6\n' > gains_2026a.txt
printf '/world/EcalBarrel/module_1 1.12 5\n/world/EcalBarrel/module_2 1.25 7\n' > gains_2026b.txt
printf '/world/EcalBarrel/module_1 1.14 5\n/world/EcalBarrel/module_2 1.27 7\n' > gains_2026c.txt
printf '/world/EcalBarrel/module_1 0 0 0 0 0 0\n/world/EcalBarrel/module_2 0 0 0 0 0 0\n' > alignment_nominal.txt
printf '/world/EcalBarrel/module_1 1.0 0 -3.0 0 0 0.01\n/world/EcalBarrel/module_2 0.5 0 0 0 0 0\n' > alignment_2026b.txt

ccdb add /epic/EcalBarrel/geometry  -r 0-        geometry.txt          "#from the survey of 2026" > /dev/null
ccdb add /epic/EcalBarrel/gains     -r 1-999     gains_2026a.txt       "#spring 2026 calibration" > /dev/null
ccdb add /epic/EcalBarrel/gains     -r 1000-1999 gains_2026b.txt       "#after the HV change" > /dev/null
ccdb add /epic/EcalBarrel/alignment -r 1-        alignment_nominal.txt "#nominal" > /dev/null
ccdb add /epic/EcalBarrel/alignment -r 1000-     alignment_2026b.txt   "#survey after the access of week 40" > /dev/null
sleep 2
ccdb tag pass1 -v default -t "$(date -d '1 second ago' +%Y-%m-%d-%H-%M-%S)" -c "first pass" > /dev/null
ccdb add /epic/EcalBarrel/gains     -r 1000-1999 gains_2026c.txt       "#recalibrated after pass 1" > /dev/null

echo "== ccdb vers /epic/EcalBarrel/gains"; ccdb vers /epic/EcalBarrel/gains
echo "== ccdb cat /epic/EcalBarrel/gains:1500"; ccdb cat /epic/EcalBarrel/gains:1500
echo "== ccdb cat /epic/EcalBarrel/gains:1500@pass1"; ccdb cat /epic/EcalBarrel/gains:1500@pass1

# --- the compact file: DD4hep's elements and materials, a world, and the CCDB constants of the barrel ECal
install="${DD4hepINSTALL:?DD4hepINSTALL is not set (eic-shell sets it)}"
cat > ecal.xml <<XML
<lccdd>
  <geometry open="true" close="false"/>
  <std_conditions type="NTP"/>
  <includes>
    <gdmlFile ref="$install/DDDetectors/compact/elements.xml"/>
    <gdmlFile ref="$install/DDDetectors/compact/materials.xml"/>
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
XML

# --- the job, three times; the plugins are found through the .components file on LD_LIBRARY_PATH
export LD_LIBRARY_PATH="$build/lib/CCDB/dd4hep:${LD_LIBRARY_PATH:-}"
example="$build/dd4hep/ccdb_dd4hep_example"
out500="$($example ecal.xml 500)";          echo "== run 500";        echo "$out500"
out1500="$($example ecal.xml 1500)";        echo "== run 1500";       echo "$out1500"
outtag="$($example ecal.xml 1500 pass1)";   echo "== run 1500 pass1"; echo "$outtag"

check() { echo "$1" | grep -qF -- "$2" || { echo "expected: $2" >&2; exit 1; }; }
check "$out500"  "geometry: inner_radius=105.5 mm outer_radius=160 mm length=340 mm n_sectors=48 material=PbWO4"
check "$out500"  "/world/EcalBarrel/module_1   gain=1.1 pedestal=5 ADC  delta dx=0 dz=0 mm dpsi=0 rad  aligned x=132.75 z=0 mm"
check "$out1500" "/world/EcalBarrel/module_1   gain=1.14 pedestal=5 ADC  delta dx=1 dz=-3 mm dpsi=0.01 rad  aligned x=133.75 z=-3 mm"
check "$out1500" "/world/EcalBarrel/module_2   gain=1.27 pedestal=7 ADC  delta dx=0.5 dz=0 mm dpsi=0 rad  aligned x=-132.25 z=0 mm"
check "$outtag"  "/world/EcalBarrel/module_1   gain=1.12 pedestal=5 ADC  delta dx=1 dz=-3 mm dpsi=0.01 rad  aligned x=133.75 z=-3 mm"
echo "ccdb_dd4hep_example: geometry, gains and alignment come from CCDB; the tag keeps the earlier gains"
