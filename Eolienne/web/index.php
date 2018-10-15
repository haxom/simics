<?php
	/*
	@author haxom <haxom@haxom.net>
	@version 0.1
	*/

	// import PhpModbus
	require_once './phpmodbus/ModbusMaster.php';
	$modbus = new ModbusMaster("172.17.0.1", "TCP");
	$modbus->port = "5002";
	$modbus->client_port = "5002";
	$unitId = 0;

	$body = "";

	if(isset($_GET['act']) && !empty($_GET['act']))
	{
		$act = $_GET['act'];
		$body = $act;

		switch($act)
		{
			case "show":
				try {
					$coils = $modbus->readCoils($unitId, 0, 2);
					$registers = $modbus->readMultipleRegisters($unitId, 0, 2);
					$body = var_dump($coils);
					$body .= '<br />'.chr(10).var_dump($registers);
				}
				catch(Exception $e)
				{
					$body = $e;
				}
				break;
		}
	}
?>
<html>
<head>
	<title>EolienneMonitor</title>
</head>
<body>
<h3>Coils</h3>
<?php
	foreach($coils as $id => $coil)
		print '['.$id.'] => '.$coil.' <br />';
?>
<h3>Registers</h3>
<?php
	foreach($registers as $id => $register)
		print '['.$id.'] => '.$register.' <br />';
?>
</body>
</html>
