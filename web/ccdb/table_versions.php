<?php
include_once('./lib/tbs_class.php');
require_once("./config.php");

//Validate request
if (!isset($_REQUEST['path'])) 
{
    $TBS = new clsTinyButStrong;
	$TBS->LoadTemplate('./templates/directory_not_found.html');
    $TBS->Show();
}

$directory_path = $_REQUEST["path"];
$ajax_parameters = "?op=vers";

//$name = "John";

$TBS = new clsTinyButStrong;
$TBS->LoadTemplate('./templates/table_versions.html');
$TBS->Show();
?>