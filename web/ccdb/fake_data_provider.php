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
	   { "text": "1. Pre Lunch (120 min) <a href=\"http://google.com\">go</a> ", 
		 "classes": "folder", 
		 "children": 
		    [ 
			    { "text": "1.1 The State of the Powerdome (30 min)<a href=\"http://google.com\">go</a>" }, 
				{ "text": "1.2 The Future of jQuery (30 min)" }, 
				{ "text": "1.2 jQuery UI - A step to richnessy (60 min)" } 
			] 
		}, 
		{ "text": "2. Lunch (60 min)" }, 
		{ "text": "3. After Lunch (120+ min)"} 
	]';
}
elseif($op==="data")
{
	echo '{ "aaData": [
	["0", "2147483647", "default", "10/31/2009 15:08", "2009-10-31 15:08"],
  	["0", "2147483647", "default", "10/28/2011 14:11", "2011-10-28 14:11"],
  	["1", "1000"      , "default", "10/27/2011 15:08", "2011-10-27 15:08"],
  	["0", "2147483647", "dmitry" , "09/14/2011 16:19", "2011-09-14 16:19"]
	],
	"aaColumns": ["opa", "apa", "tet","sum", "soho"	],
	"aaComments":"This is a test table we should be glad we have it!"
	
	}';
	//
	
}
?>

