<?php

if(!isset($_REQUEST["op"])) 
{
  echo "No op is set";
  exit(0);
}
$op = strtolower($_REQUEST["op"]);

if($op === "vers")
{
//The array is run-min, run-max, variation, date 
  echo '{ "aaData": [
	["0","2147483647","default","10/31/2009 15:08","2009-10-31 15:08"],
  ["0","2147483647","default","10/28/2011 14:11","2011-10-28 14:11"],
  ["1","1000","default","10/27/2011 15:08","2011-10-27 15:08"],
  ["0","2147483647","dmitry","09/14/2011 16:19","2011-09-14 16:19"]
]}';

}
elseif($op==="objlist")
{
	echo '
	[ 
	   { "text": "test", 
		 "classes": "folder", 
		 "children": 
		    [ 
			    { "text": "test_vars" }, 
				{ "text": "test_vars2" }, 
				{ "text": "subfolder_for_tesing", "classes": "folder" } 
			] 
		}, 
		{ "text": "CDC", "classes": "folder", 
		 "children": 
		    [ 
			    { "text": "test_vars" }, 
				{ "text": "test_vars2" }, 
				{ "text": "subfolder_for_tesing" } 
			] },
        { "text": "PMT", "classes": "folder" , 
		 "children": 
		    [ 
			    { "text": "test_vars" }, 
				{ "text": "test_vars2" }, 
				{ "text": "subfolder_for_tesing" } 
			] }, 
		{ "text": "ADC", "classes": "folder", 
		 "children": 
		    [ 
			    { "text": "test_vars" }, 
				{ "text": "test_vars2" }, 
				{ "text": "subfolder_for_tesing" } 
			] },
        { "text": "Magnet", "classes": "folder", 
		 "children": 
		    [ 
			    { "text": "test_vars" }, 
				{ "text": "test_vars2" }, 
				{ "text": "subfolder_for_tesing" } 
			] } 
	]';
}
elseif($op==="data")
{

echo '{ "aaData": [
["1.12", "5.987", "0.99245", "10.22", "coil 1"],
["1.13", "5.987", "0.1235234", "12.12", "coil 2"],
["1.11", "6.988", "0.123236", "0", "coil 3"],
["2.23", "5.957", "0.99276", "0", "coil 4"],
["1.53", "5.981", "0.929486", "0", "coil 5"],
["1.55", "5.987", "0.23486", "1.12", "coil 6"],
["1.10", "5.987", "0.2343", "5.34e-10", "coil 7"],
["0.21", "5.987", "0.22423", "0.115", "coil 8"],
["0.89", "5.987", "0.296884", "1923.12", "coil 9"],
["1.11", "5.987", "0.230967", "1.00123", "coil 10"]

],
"aaColumns": ["c0", "c1", "c2","c3", "description"	],
"aaComments":"This is a test table. It has 5 columns and 10 rows with. 4 columns contains double values, last column is string containing description. "

}';

/*
echo '{ "aaData": [
["0", "2147483647", "default", "10/31/2009 15:08", "2009-10-31 15:08"],
["0", "2147483647", "default", "10/28/2011 14:11", "2011-10-28 14:11"],
["1", "1000"      , "default", "10/27/2011 15:08", "2011-10-27 15:08"],
["0", "2147483647", "dmitry" , "09/14/2011 16:19", "2011-09-14 16:19"]
],
"aaColumns": ["opa", "apa", "tet","sum", "soho"	],
"aaComments":"This is a test table we should be glad we have it!"

}';
*/	//
	
}
?>

