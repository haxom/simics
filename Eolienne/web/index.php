<?php
	/*
	@author haxom <haxom@haxom.net>
	@version 0.1
	*/

	// import PhpModbus
	require_once './phpmodbus/ModbusMaster.php';
	$modbus = new ModbusMaster("127.0.0.1", "TCP");
	$modbus->port = "5002";
	$modbus->client_port = "5002";
	$unitId = 66; // 0x42

	if(isset($_GET['act']) && !empty($_GET['act']))
	{
		$act = $_GET['act'];

		switch($act)
		{
			case "readAll":
				$output = Array();
				$output['coils'] = $modbus->readCoils($unitId, 0, 2);
				$output['broken'] = $modbus->readCoils($unitId, 25, 1);
				$registers = array_chunk($modbus->readMultipleRegisters($unitId, 0, 2), 2);
				foreach($registers as $key => $value)
					$output['registers'][$key] = PhpType::bytes2unsignedInt($value);
				print json_encode($output);
				exit();

			case "manualStop":
				$modbus->writeMultipleCoils($unitId, 0, [0]);
				exit();
			case "manualStart":
				$modbus->writeMultipleCoils($unitId, 0, [1]);
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
		var broken = false;

		function updateCoils()
		{
			var div_manual = document.getElementById('div_status_manual');
			var button_stop = document.getElementById('button_stop');
			var div_auto = document.getElementById('div_status_auto');
			var button_start = document.getElementById('button_start');
			if(coils[0] == false)
			{
				div_manual.style.backgroundColor = "red";
				button_stop.disabled = true;
				button_start.disabled = false;
			}
			if(coils[0] == true)
			{
				div_manual.style.backgroundColor = "green";
				button_stop.disabled = false;
				button_start.disabled = true;
			}
			if(coils[1] == false)
				div_auto.style.backgroundColor = "red";
			if(coils[1] == true)
				div_auto.style.backgroundColor = "green";
		}

		function updateRegisters()
		{
			document.getElementById('input_wind_speed').value = registers[0] + " m/s";
			document.getElementById('input_power_production').value = registers[1] + " kW";
		}

		function updateBroken()
		{
			if(broken)
				document.getElementById('img_eolienne').src = "eolienne_broken.png";
			else
				document.getElementById('img_eolienne').src = "eolienne.png";
			
		}

		function manualStop()
		{
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					updateCoils();
					updateRegisters();
				}
			}
			xhr.open('GET', 'index.php?act=manualStop', true);
			xhr.send(null);
		}

		function manualStart()
		{
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					updateCoils();
					updateRegisters();
				}
			}
			xhr.open('GET', 'index.php?act=manualStart', true);
			xhr.send(null);
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
					broken = results['broken'][0]
					updateCoils();
					updateRegisters();
					updateBroken();
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
<center>
<table style="border-collapse: collapse;" width="80%">
<tr>
<td width="10%" style="border: 1px solid black;" valign="top">
<center><b>[ STATUS ]</b></center><br />
<div id="div_status_manual" style="border-radius: 5px; border: 1px solid black; display: inline;background-color: red;" width="25px">&nbsp; &nbsp; &nbsp; &nbsp;</div> Manual<br /><br />
<div id="div_status_auto" style="border-radius: 5px; border: 1px solid black; display: inline; background-color: red;" width="25px">&nbsp; &nbsp; &nbsp; &nbsp;</div> Automatic<br /> <br />

<center><b>[ ACTIONS ]</b></center><br />
<center>
<input style="text-align: center" onclick="manualStart()" type="button" id="button_start" value="START" disabled><br />
<input style="text-align: center" onclick="manualStop()" type="button" id="button_stop" value="STOP" disabled>
</center>
</td>
<td width="5%" style="text-align: center; border: 1px solid black" valign="top">
Wind speed <input style="text-align: center;" id="input_wind_speed" value="0 m/s" readonly>
</td>
<td width="80%" style="border: 1px solid black;">
<center><img id="img_eolienne" src="eolienne.png"></center>
</td>
<td width="5%" style="border: 1px solid black; text-align: center" valign="bottom">
Power production (instant) <input style="text-align: center;" id="input_power_production" value="0 kW" readonly>
</td>
</tr>
</table>
</center>
</body>
</html>
