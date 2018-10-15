<?php
	/*
	@author	haxom <haxom@haxom.net>
	@version 1.0
	*/

	// import PhpModbus
	require_once './phpmodbus/ModbusMaster.php';
	$modbus = new ModbusMaster("172.17.0.1", "TCP");
	$modbus->port = "5002";
	$modbus->client_port = "5002";
	$unitId = 0;

	if(isset($_GET['act']) && !empty($_GET['act']))
	{
		$act = $_GET['act'];

		switch($act)
		{
			case "readAll":
				try {
					$coils = $modbus->readCoils($unitId, 0, 20);
					// $registers = $modbus->readMultipleRegisters($unitId, 0, 2);
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
	<title>TemplateMonitor</title>
</head>
<body>
<center><h1>TemplateMonitor</h1></center>
<h3>Coils</h3>
<?php
	if(isset($coils))
	{
		foreach($coils as $id => $coil)
		{
			if($coil)
				print '['.$id.'] => True <br />';
			else
				print '['.$id.'] => False <br />';
		}
	}
				
/*
?>
<h3>Registers</h3>
<?php
	foreach($registers as $id => $register)
		print '['.$id.'] => '.$register.' <br />';
*/
?>
</body>
</html>
