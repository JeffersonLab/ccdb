<?php
include_once('./lib/tbs_class.php');
require_once("./config.php");

//Validate request
if (!isset($_REQUEST['request'])) 
{
    $TBS = new clsTinyButStrong;
    $TBS->LoadTemplate('./templates/request_not_found.html');
    $TBS->Show();
}

$data_request = $_REQUEST["request"];

$TBS = new clsTinyButStrong;
$TBS->LoadTemplate('./templates/table_data.html');
$TBS->Show();
?>
