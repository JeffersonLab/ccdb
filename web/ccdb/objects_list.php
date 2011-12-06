<?php
include_once('./lib/tbs_class.php');
require_once("./config.php");

//$name = "John";

$TBS = new clsTinyButStrong;
$TBS->LoadTemplate('./templates/objects_list.html');
$TBS->Show();


?>