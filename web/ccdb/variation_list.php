<?php
include_once('./lib/tbs_class.php');
require_once("./config.php");

$ajax_parameters = "?op=vars";

//$name = "John";

$TBS = new clsTinyButStrong;
$TBS->LoadTemplate('./templates/variation_list.html');
$TBS->Show();

?>

