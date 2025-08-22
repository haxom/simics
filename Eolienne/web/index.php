<?php
	/*
	@author haxom <haxom@haxom.net>
	@version 1.3
	*/

    // start session
    session_start();

	// import PhpModbus
	require_once './phpmodbus/Phpmodbus/ModbusMaster.php';
	$modbus = new ModbusMaster("127.0.0.1", "TCP");
	$modbus->port = "502";
	$modbus->client_port = "502";
	$unitId = 66; // 0x42

	if(isset($_GET['act']) && !empty($_GET['act']))
	{
		$act = $_GET['act'];

		switch($act)
		{
			case "readAll":
				$output = Array();
				$output['coils'] = $modbus->readCoils($unitId, 0, 2);
				$output['broken'] = $modbus->readInputDiscretes($unitId, 40, 1);
				$registers = array_chunk(array: $modbus->readMultipleRegisters($unitId, 0, 12), length: 2);
				foreach($registers as $key => $value)
					$output['registers'][$key] = PhpType::bytes2unsignedInt($value);
				print json_encode(value: $output);
				exit();

			case "manualStop":
                if(isset($_SESSION['auth']) && $_SESSION['auth'] == 'operator')
				    $modbus->writeMultipleCoils($unitId, 0, [0]);
				exit();
			case "manualStart":
                if(isset($_SESSION['auth']) && $_SESSION['auth'] == 'operator')
				    $modbus->writeMultipleCoils($unitId, 0, [1]);
				exit();
            case "auth":
                if(isset($_GET['pass']) && $_GET['pass'] === apache_getenv(variable: 'OPERATOR_PWD'))
                {
                    $_SESSION['auth'] = 'operator';
                    print "ok";
                }
                exit();
            case "deauth":
                // remove all session variables
                session_unset();
                // destroy the session
                session_destroy();
                exit();
		}
	}
?>
<!DOCTYPE html>
<head>
	<title>TURBOELEC - Supervision Eolienne</title>
	<style>
		@keyframes blink {
			0%, 100% {opacity: 1;}
			50% {opacity: 0;}
		}
	</style>
	<script>
		var coils = new Array();
		var registers = new Array();
		var broken = false;

        var auth = "anonymous";
        <?php
            if(isset($_SESSION['auth']) && $_SESSION['auth'] == 'operator')
                echo "auth = \"operator\";";
        ?>

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
                if(auth == "operator")
				    button_start.disabled = false;
			}
			if(coils[0] == true)
			{
				div_manual.style.backgroundColor = "green";
                if(auth == "operator")
				    button_stop.disabled = false;
				button_start.disabled = true;
			}
			if(coils[1] == false)
				div_auto.style.backgroundColor = "red";
			if(coils[1] == true)
				div_auto.style.backgroundColor = "green";

			// images status
			var img_run = document.getElementById('status_img_run');
			var img_stop = document.getElementById('status_img_stop');
			var img_warning = document.getElementById('status_img_warning');
			var img_error = document.getElementById('status_img_error');

			if(coils[0] == true && coils[1] == true)
			{
				img_run.style.display = "inline";
				img_stop.style.display = "none";
				img_warning.style.display = "none";
			}
			else
			{
				img_run.style.display = "none";
				img_stop.style.display = "inline";
				img_warning.style.display = "none";
			}
			if(coils[1] == false)
			{
				img_warning.style.display = "inline";
			}
		}

		function updateRegisters()
		{
			document.getElementById('input_pitch_angle').value = registers[0] + " °";
			document.getElementById('input_wind_speed').value = registers[1] + " m/s";
			document.getElementById('input_rotor_speed').value = registers[2] + " RPM (" + Math.round((registers[2] / registers[3]) * 100) + " %)";
			document.getElementById('input_yaw_position').value = registers[4] + " °";
			//document.getElementById('input_temperature').value = registers[5] + " °C";
			document.getElementById('input_mech_power_production').value = registers[10] + " kW";
			document.getElementById('input_elec_power_production').value = registers[11] + " kW";
		}

		function updateBroken()
		{
			if(broken)
			{
				document.getElementById('status_img_error').style.display = "inline";
				document.getElementById('status_img_warning').style.display = "none";
				document.getElementById('status_img_run').style.display = "none";
				document.getElementById('status_img_stop').style.display = "none";
				document.getElementById('button_start').disabled = true;
				document.getElementById('button_stop').disabled = true;
				document.getElementById('button_auth').disabled = true;
				document.getElementById('button_deauth').disabled = true;
			}
		}

		function manualStop()
		{
			if(broken)
				return;
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
			if(broken)
				return;
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

        function authent()
        {
			if(broken)
				return;
            var password = prompt("Mot de passe");
            if(password == null || password == "")
                return;

			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
                    if(this.responseText == "ok")
                        location.reload();
                    else
                        alert("Mauvais mot de passe");
			}
			xhr.open('GET', 'index.php?act=auth&pass='+password, true);
			xhr.send(null);
        }

        function deauthent()
        {
			if(broken)
				return;
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
                    location.reload();
			}
			xhr.open('GET', 'index.php?act=deauth', true);
			xhr.send(null);
        }

		function updateData()
		{
			if(broken)
				return;
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
<center><h1>TURBOELEC - Supervision Eolienne</h1></center>
<center>
<table style="border-collapse: collapse;" width="860px">
<tr>
<td width="150px" style="border: 1px solid black;" valign="top">
<center><b>[ Turbine State ]</b></center><br />
<div id="div_status_manual" style="border-radius: 5px; border: 1px solid black; display: inline;background-color: red;" width="25px">&nbsp; &nbsp; &nbsp; &nbsp;</div> Manual<br /><br />
<div id="div_status_auto" style="border-radius: 5px; border: 1px solid black; display: inline; background-color: red;" width="25px">&nbsp; &nbsp; &nbsp; &nbsp;</div> Automatic<br /> <br />
<div id="div_status" style="text-align: center;">
    <img src="pics/run.png" id="status_img_run" style="display: none" width="25px" height="25px">
    <img src="pics/stop.png" id="status_img_stop" style="display: none" width="25px" height="25px">
    <img src="pics/warning.png" id="status_img_warning" style="display: none" width="25px" height="25px">
    <img src="pics/error.png" id="status_img_error" style="display: none; animation: blink 1s infinite;" width="25px" height="25px">
    <br /><br />
</div>
<center><b>[ Operator ]</b></center><br />
<center>
<input style="text-align: center" onclick="manualStart()" type="button" id="button_start" value="START" disabled><br />
<input style="text-align: center" onclick="manualStop()" type="button" id="button_stop" value="STOP" disabled>
<br /><br /><br />
<?php
if(isset($_SESSION['auth']) && $_SESSION['auth'] == 'operator')
{
?>
<input style="text-align: center" onclick="deauthent()" type="button" id="button_deauth" value="Disconnect">
<?php
}
else
{
?>
<input style="text-align: center" onclick="authent()" type="button" id="button_auth" value="Connect">
<?php
}
?>
</center>
</td>
<td width="180px" style="text-align: center; border: 1px solid black" valign="top">
    Mechanical power production (instant) <input style="text-align: center;" id="input_mech_power_production" value="0 kW" readonly><br /><br />
    Electrical power production (instant) <input style="text-align: center;" id="input_elec_power_production" value="0 kW" readonly>
</td>
<td width="350px" style="border: 1px solid black;">
<img id="img_eolienne" src="pics/eolienne.png" width="350px" height="576px">
</td>
<td width="180px" style="border: 1px solid black; text-align: center" valign="bottom">

<table  style="border-collapse: collapse; height: 576px;" width="100%">
    <tr style="border: 0px; height: 28px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">&nbsp;</td>
    </tr>
    <tr style="border: 0px; height: 30px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">
        Pitch angle <br /><input style="text-align: center;" id="input_pitch_angle" value="0 °" readonly>
        </td>
    </tr>

    <tr style="border: 0px; height: 112px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">&nbsp;</td>
    </tr>
    <tr style="border: 0px; height: 30px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">
        Wind speed <br /><input style="text-align: center;" id="input_wind_speed" value="0 m/s" readonly>
        </td>
    </tr>
    <tr style="border: 0px; height: 30px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">
        Rotor speed <br /><input style="text-align: center;" id="input_rotor_speed" value="0 RPM (0 %)" readonly>
        </td>
    </tr>
    <tr style="border: 0px; height: 30px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">
        Yaw position <br /><input style="text-align: center;" id="input_yaw_position" value="0 °" readonly>
        </td>
    </tr>

    <tr style="border: 0px; height: 50px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">&nbsp;</td>
    </tr>
    <tr style="border: 0px; height: 30px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">
        <!-- not implemented yey
        Temperature <br /><input style="text-align: center;" id="input_temperature" value="0 °" readonly>
        -->
        </td>
    </tr>
    
    <tr style="border: 0px; height: 220px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">&nbsp;</td>
    </tr>
	<tr style="border: 0px; height: 20px;">
        <td style="text-align: center; border: 0px; vertical-align: middle">	
			<a href="https://en.wind-turbine-models.com/turbines/274-vestas-v27" target="_blank">Vestas V27</a>
		</td>
    </tr>
</table>
</td>
</tr>
</table>
</center>
</body>
</html>