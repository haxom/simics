<?php
	/*
	@author haxom <haxom@haxom.net>
	@version 0.1
	*/

	// import PhpModbus
	require_once './phpmodbus/ModbusMaster.php';

	// import IP list of Eoliennes
	$eoliennes = explode(';', file_get_contents('eoliennes.txt'));
	$md = Array();
	$id = 0;
	foreach($eoliennes as $eolienne)
	{
		$md[$id] = new ModbusMaster($eolienne, "TCP");
		$md[$id]->port = "502";
		$md[$id]->client_port = 502;
		$id++;
	}
	$unitId = 66; // 0x42

	if(isset($_GET['act']) && !empty($_GET['act']))
	{
		$act = $_GET['act'];

		switch($act)
		{
			case "readAll":
				$id = 0;
				$output = Array();
				foreach($md as $modbus)
				{
					$output[$id] = Array();
					$output[$id]['ip'] = $modbus->host;
					$output[$id]['coils'] = $modbus->readCoils($unitId, 0, 2);
					$registers = array_chunk($modbus->readMultipleRegisters($unitId, 0, 2), 2);
					foreach($registers as $key => $value)
						$output[$id]['registers'][$key] = PhpType::bytes2unsignedInt($value);
					$id+=1;
				}
				print json_encode($output);
				exit();

			case "manualStop":
				if(isset($_GET['id']))
				{
					$id = intval($_GET['id']);
					$modbus = $md[$id];
					$modbus->writeMultipleCoils($unitId, 0, [0]);
				}
				exit();
			case "manualStart":
				if(isset($_GET['id']))
				{
					$id = intval($_GET['id']);
					$modbus = $md[$id];
					$modbus->writeMultipleCoils($unitId, 0, [1]);
				}
				exit();
		}
	}
?>
<html>
<head>
	<title>UsineEol</title>
	<script>
		var eoliennes = new Array();
		var production = 0;
		var eol_up = 0;

		function updateView()
		{
			production = 0;
			eol_up = 0;
			table = document.getElementById("table_eoliennes");
			for(i=0;i<eoliennes.length;i++)
			{
				eol = eoliennes[i];
				id = i;
				eol_state = true;
				if(table.rows.length > i+1)
					row = table.deleteRow(i+1);
				row = table.insertRow(i+1);
				row.className = "font-fixed-width";
				row.id="eol_"+id;
				row.ip=eol["ip"];

				state_manual = "red";
				statue_auto = "red";
				button_stop_dis = "disabled"
				button_start_dis = "";

				if(eol['coils'][0] == false)
				{
					state_manual = "red";
					button_stop_dis = "disabled";
					button_start_dis = "";
					eol_state = false;
				}
				if(eol['coils'][0] == true)
				{
					state_manual = "green";
					button_stop_dis = "";
					button_start_dis = "disabled";
				}
				if(eol['coils'][1] == false)
				{
					state_auto = "red";
					eol_state = false;
				}
				if(eol['coils'][1] == true)
				{
					state_auto = "green";
				}
				
				if(eol_state)
					eol_up += 1;

				// status
				cell = row.insertCell(0);
				cell.align = "center"
				cell.innerHTML = "<div id=\"div_status_manual_"+id+"\" style=\"border-radius: 5px; border: 1px solid black; display: inline;background-color: "+state_manual+";\" width=\"25px\">&nbsp; &nbsp; &nbsp; &nbsp;</div> Manual | <div id=\"div_status_auto"+id+"\" style=\"border-radius: 5px; border: 1px solid black; display: inline; background-color: "+state_auto+";\" width=\"25px\">&nbsp; &nbsp; &nbsp; &nbsp;</div> Automatic";

				// wind speed
				cell = row.insertCell(1);
				cell.align = "center";
				cell.innerHTML = "<input style=\"text-align: center;\" id=\"input_wind_speed_"+id+"\" value=\""+eol["registers"][0]+" m/s\" readonly>";

				// power production (instant)
				cell = row.insertCell(2);
				cell.align = "center";
				cell.innerHTML = "<input style=\"text-align: center;\" id=\"input_power_production_"+id+"\" value=\""+eol["registers"][1]+" kW\" readonly>";
				production += eol["registers"][1];

				// action
				cell = row.insertCell(3);
				cell.align = "center";
				cell.innerHTML = "<input syle=\"text-align: center\" onclick=\"manualStart('"+id+"')\" type=\"button\" id=\"button_start_"+id+"\" value=\"start\" "+button_start_dis+"> <input syle=\"text-align: center\" onclick=\"manualStop('"+id+"')\" type=\"button\" id=\"button_start_"+id+"\" value=\"stop\" "+button_stop_dis+">";

				// adresse IP
				cell = row.insertCell(4);
				cell.align = "center";
				cell.innerHTML = "<a href=\"http://"+eol['ip']+"\" target=\"_blank\">"+eol['ip']+"</a>";

			}
			for(i=table.rows.length-1;i>eoliennes.length;i--)
				table.deleteRow(i);

			document.getElementById('global_stat').innerHTML = "Production globale (instant) : <b>"+production+" kW</b> | Éoliennes actives : "+eol_up+" / "+eoliennes.length;
		}

		function manualStop(id)
		{
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
					updateData();
			}
			xhr.open('GET', 'index.php?act=manualStop&id='+id, true);
			xhr.send(null);
		}

		function manualStart(id)
		{
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
					updateData();
			}
			xhr.open('GET', 'index.php?act=manualStart&id='+id, true);
			xhr.send(null);
		}

		function updateData()
		{
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					eoliennes = JSON.parse(this.responseText);
					updateView();
				}
			}
			xhr.open('GET', 'index.php?act=readAll', true);
			xhr.send(null);
		}

		setInterval(updateData, 500);
	</script>
</head>
<body>
<center><h1>UsineEol</h1></center>
<center><div id="global_stat"></div>
</center>
<center>
<table style="border-collapse: collapse;" width="80%" id="table_eoliennes">
<tr>
<td width="20%" style="border: 1px solid black;" align="center" valign="top">Status</td>
<td width="25%" style="border: 1px solid black;" align="center" valign="top">Wind speed</td>
<td width="25%" style="border: 1px solid black;" align="center" valign="top">Power production (instant)</td>
<td width="20%" style="border: 1px solid black;" align="center"valign="top">Actions</td>
<td width="10%" style="border: 1px solid black;" align="center"valign="top">Adresse IP</td>
</tr>
</table>
</center>
</body>
</html>
