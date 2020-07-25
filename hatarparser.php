<?php
require "../../php_secrets/hatarparser_recorder.php";

$inputJSON = file_get_contents('php://input');
$request = json_decode($inputJSON, TRUE);
$rq_key = $request["key"];
if(!isset($hatarhelyzet_key) || !isset($rq_key) || $rq_key != $hatarhelyzet_key){
    http_response_code(404);
	die();
}
if(!isset($request["payload"])){
	exit("Missing arguments");
}
$conn = new mysqli($servername, $username, $password, $dbname);

if($conn->connect_error){
	exit("Connection failed: " . $conn->connect_error);
}
if (!$conn->set_charset("utf8")) {
    printf("Error loading character set utf8: %s\n", $conn->error);
    exit();
} 
$BORDER_INSERT = $conn->prepare("INSERT IGNORE INTO hatarinfo (id, country, border_hun, border_other, openings, transport_types, alternate_border, seen) VALUES (?,?,?,?,?,?,?,?)");
$BORDER_INSERT->bind_param("ssssssss", $border_id, $country, $border_hun, $border_other, $openings, $transport_types, $alternate_border, $seen);
$BORDER_INFO_INSERT = $conn->prepare("INSERT IGNORE INTO hatarhelyzet (id, dir, transport_type, waiting_time) VALUES(?,?,?,?)");
$BORDER_INFO_INSERT->bind_param("ssss", $helyzet_id, $dir, $transport_type, $waiting_time);
$BORDER_INFO_PAIR_INSERT = $conn->prepare("INSERT INTO hatarhelyzetinfo (hatarinfo_id, hatarhelyzet_id, seen) VALUES(?,?,?)");
$BORDER_INFO_PAIR_INSERT->bind_param("sss", $border_id, $helyzet_id, $seen);

$payload = $request["payload"];
$borders = $payload["borders"];
$info = $payload["info"];
$border_info = $payload["border_info"];
$conn->query("START TRANSACTION");
foreach($borders as $border){
    list($border_id, $country, $border_hun, $border_other, $openings, $transport_types, $alternate_border, $seen) = $border;
    $BORDER_INSERT->execute();
}
foreach($info as $i){
    list($helyzet_id, $dir, $transport_type, $waiting_time) = $i;
    $BORDER_INFO_INSERT->execute();
}
foreach($border_info as $bi){
    list($border_id, $helyzet_id, $seen) = $bi;
    $BORDER_INFO_PAIR_INSERT->execute();
}
$conn->query("COMMIT");

$BORDER_INSERT->close();
$BORDER_INFO_INSERT->close();
$BORDER_INFO_PAIR_INSERT->close();

echo "OK";
?>

