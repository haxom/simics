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

	if(isset($_GET['act']) && !empty($_GET['act']))
	{
		$act = $_GET['act'];

		switch($act)
		{
			case "readAll":
				$output = Array();
				$output['coils'] = $modbus->readCoils($unitId, 0, 2);
				$output['registers'] = $modbus->readMultipleRegisters($unitId, 0, 2);
				print json_encode($output);
				exit();
		}
	}
?>
<html>
<head>
	<title>EolienneMonitor</title>
	<script>
		var coils = new Array();
		var registers = new Array();

		function updateCoils()
		{
			html = "";
			for(var i in coils)
				html += "["+i+"] => "+coils[i]+"<br />";
			document.getElementById('div_coils').innerHTML = html;
		}

		function updateRegisters()
		{
			html = "";
			for(var i in registers)
				html += "["+i+"] => "+registers[i]+"<br />";
			document.getElementById('div_registers').innerHTML = html;

		}

		function updateData()
		{
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					var results = JSON.parse(this.responseText);
					coils = results['coils'];
					registers = results['registers'];
					updateCoils();
					updateRegisters();
				}
			}
			xhr.open('GET', 'index.php?act=readAll', true);
			xhr.send(null);
		}

		setInterval(updateData, 500);
	</script>
</head>
<body>
<center><h1>EolienneMonitor</h1></center>
<h3>Coils</h3>
<div id="div_coils">
</div>
<h3>Registers</h3>
<div id="div_registers">
</div>
</body>
</html>
