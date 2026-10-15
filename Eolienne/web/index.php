<?php
	/*
		@author haxom <haxom@haxom.net>
		@version 1.10
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
				$limit_value_registers = array_chunk(array: $modbus->readMultipleRegisters($unitId, 20, 6), length: 2);
				foreach($limit_value_registers as $key => $value)
					$output['limit_value_registers'][$key] = PhpType::bytes2unsignedInt($value);
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

			case "ascStatus":
				// Proxy vers l'API REST ascenseur (loopback dans le conteneur).
				// Le navigateur de l'operateur est hors du conteneur : il ne
				// peut pas joindre 127.0.0.1:8080, c'est donc PHP qui relaie.
				header('Content-Type: application/json');
				$ctx = stream_context_create(array('http' => array('timeout' => 1)));
				$response = @file_get_contents('http://127.0.0.1:8080/api/status', false, $ctx);
				if($response === false)
				{
					http_response_code(502);
					print json_encode(array('error' => 'ascenseur api unavailable'));
				}
				else
				{
					print $response;
				}
				exit();

			case "ascCommand":
				// Relaie une commande ascenseur - reserve a l'operateur authentifie.
				header('Content-Type: application/json');
				if(!isset($_SESSION['auth']) || $_SESSION['auth'] != 'operator')
				{
					http_response_code(403);
					print json_encode(array('error' => 'forbidden'));
					exit();
				}
				$cmd = isset($_GET['cmd']) ? $_GET['cmd'] : '';
				if(!in_array($cmd, array('up', 'down', 'stop'), true))
				{
					http_response_code(400);
					print json_encode(array('error' => 'invalid command'));
					exit();
				}
				$ctx = stream_context_create(array('http' => array(
					'method'  => 'POST',
					'header'  => "Content-Type: application/json\r\n",
					'content' => json_encode(array('command' => $cmd)),
					'timeout' => 1,
				)));
				$response = @file_get_contents('http://127.0.0.1:8080/api/command', false, $ctx);
				if($response === false)
				{
					http_response_code(502);
					print json_encode(array('error' => 'ascenseur api unavailable'));
				}
				else
				{
					print $response;
				}
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
		.ascenseur_btn {
			font-size: 14px;
			padding: 6px 12px;
			margin: 2px;
			cursor: pointer;
		}
		.ascenseur_btn:disabled {
			cursor: not-allowed;
			opacity: 0.5;
		}
	</style>
	<script>
		var coils = new Array();
		var registers = new Array();
		var broken = false;
		var ascenseur = null;
		var maintenance_ok = false;

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
			if(coils[0] == false)
			{
				div_manual.style.backgroundColor = "red";
				button_stop.disabled = true;
			}
			if(coils[0] == true)
			{
				div_manual.style.backgroundColor = "green";
                if(auth == "operator")
				    button_stop.disabled = false;
			}
			if(coils[1] == false)
				div_auto.style.backgroundColor = "red";
			if(coils[1] == true)
				div_auto.style.backgroundColor = "green";

			// status
			var img_run = document.getElementById('status_img_run');
			var img_stop = document.getElementById('status_img_stop');
			var img_warning = document.getElementById('status_img_warning');
			var text_warning = document.getElementById('warning_text');

            switch (limit_value_registers[5])
            {
                case 1:
                    text_warning.textContent = "wind speed too low/high";
                    break;
                case 2:
                    text_warning.textContent = "RPM too fast";
                    break;
                case 0:
                default:
                    text_warning.textContent = "";
            }

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

			// Mise à jour indicateur sécurité ascenseur
			maintenance_ok = (coils[0] == false);
			var div_maintenance = document.getElementById('div_maintenance_auth');
			if(maintenance_ok)
			{
				div_maintenance.style.backgroundColor = "green";
				div_maintenance.textContent = "MAINTENANCE AUTORISÉE";
			}
			else
			{
				div_maintenance.style.backgroundColor = "red";
				div_maintenance.textContent = "MAINTENANCE INTERDITE";
			}

			// Mise à jour des boutons ascenseur
			updateAscenseurButtons();

			// Blocage du démarrage tant qu'une maintenance est en cours
			updateStartButton();
		}

		function updateRegisters()
		{
			document.getElementById('input_pitch_angle').value = registers[0] + " °";
			document.getElementById('input_wind_speed').value = registers[1]/100 + " m/s";
			document.getElementById('input_rotor_speed').value = registers[2] + " RPM (" + Math.round((registers[2] / limit_value_registers[2]) * 100) + " %)";
			document.getElementById('input_yaw_position').value = registers[3] + " °";
			//document.getElementById('input_temperature').value = registers[4] + " °C";
			document.getElementById('input_mech_power_production').value = registers[10] + " kW";
			document.getElementById('input_elec_power_production').value = registers[11] + " kW";
		}

		function updateBroken()
		{
			if(broken)
			{
				document.getElementById('status_error').style.display = "inline";
				document.getElementById('status_text_error').style.display = "inline";
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

		// --- Fonctions Ascenseur ---

		function updateAscenseur()
		{
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					if(this.status != 200 || this.responseText == "")
					{
						console.error("API ascenseur indisponible (HTTP " + this.status + ")");
						return;
					}
					try {
						ascenseur = JSON.parse(this.responseText);
						updateAscenseurUI();
					} catch(e) {
						console.error("Erreur API ascenseur:", e);
					}
				}
			}
			xhr.onerror = function() { console.error("API ascenseur injoignable"); };
			// Meme origine que l'IHM : PHP fait le relais vers 127.0.0.1:8080
			xhr.open('GET', 'index.php?act=ascStatus', true);
			xhr.send(null);
		}

		function updateAscenseurUI()
		{
			if(!ascenseur) return;

			// Position texte
			var pos_text = document.getElementById('ascenseur_position_text');
			if(pos_text) pos_text.textContent = ascenseur.position + " %";

			// Position cabine SVG : translation du groupe (cabine + Nacelle + porte)
			var cabine_g = document.getElementById('ascenseur_cabine_g');
			if(cabine_g)
			{
				var dy = -(ascenseur.position / 100) * 250;
				cabine_g.setAttribute('transform', 'translate(0,' + dy + ')');
			}

			// État
			var state_text = document.getElementById('ascenseur_state');
			var state_map = {0: "ARRÊTÉ", 1: "MONTÉE", 2: "DESCENTE", 3: "ERREUR", 4: "CASSÉ"};
			var state_color_map = {0: "gray", 1: "green", 2: "blue", 3: "red", 4: "red"};
			if(state_text)
			{
				state_text.textContent = state_map[ascenseur.state] || "INCONNU";
				state_text.style.color = state_color_map[ascenseur.state] || "black";
			}

			// Vitesse
			var speed_text = document.getElementById('ascenseur_speed');
			if(speed_text) speed_text.textContent = ascenseur.speed.toFixed(1) + " m/s";

			// Capteurs position
			var sensor_high = document.getElementById('ascenseur_sensor_high');
			var sensor_low = document.getElementById('ascenseur_sensor_low');
			if(sensor_high) sensor_high.setAttribute('fill', ascenseur.pos_high ? '#00ff00' : '#666666');
			if(sensor_low) sensor_low.setAttribute('fill', ascenseur.pos_low ? '#00ff00' : '#666666');

			// Porte
			var door = document.getElementById('ascenseur_door');
			if(door) door.setAttribute('fill', ascenseur.door_closed ? '#00aaff' : '#ff6600');

			// Nacelle cassée : cabine en rouge + indicateur
			var cabine = document.getElementById('ascenseur_cabine');
			if(cabine) cabine.setAttribute('fill', ascenseur.nacelle_broken ? '#cc0000' : '#ffcc00');
			var broken_div = document.getElementById('div_nacelle_broken');
			if(broken_div) broken_div.style.display = ascenseur.nacelle_broken ? "block" : "none";

			updateAscenseurButtons();
			updateStartButton();
		}

		function maintenanceInProgress()
		{
			// Maintenance en cours tant que l'ascenseur n'est pas revenu en bas
			return (ascenseur && ascenseur.position > 0);
		}

		function updateStartButton()
		{
			var button_start = document.getElementById('button_start');
			var msg = document.getElementById('maintenance_msg');
			if(!button_start) return;
			// Blocage purement IHM : contournable en écrivant directement en Modbus
			var blocked = (coils[0] == false) && maintenanceInProgress();
			// START possible seulement si opérateur + éolienne à l'arrêt + pas de maintenance en cours
			button_start.disabled = broken || !(auth == "operator" && coils[0] == false) || blocked;
			if(msg) msg.style.display = blocked ? "block" : "none";
		}

		function updateAscenseurButtons()
		{
			var buttons = document.querySelectorAll('.ascenseur_btn');
			var has_error = (ascenseur && (ascenseur.state == 3 || ascenseur.state == 4));
			buttons.forEach(function(btn) {
				btn.disabled = !maintenance_ok || has_error;
			});
		}

		function sendAscenseurCommand(cmd)
		{
			if(!maintenance_ok) return;
			if(ascenseur && ascenseur.state >= 3) return;
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					if(this.status != 200)
						console.error("Echec commande ascenseur:", this.status, this.responseText);
					updateAscenseur();
					updateCoils();
				}
			}
			xhr.onerror = function() { console.error("API ascenseur injoignable"); };
			// Meme origine que l'IHM : PHP fait le relais vers 127.0.0.1:8080
			xhr.open('GET', 'index.php?act=ascCommand&cmd=' + encodeURIComponent(cmd), true);
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
					limit_value_registers = results['limit_value_registers'];
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
		setInterval(updateAscenseur, 500);
	</script>
</head>
<body>
<center><h1>TURBOELEC - Supervision Eolienne</h1></center>
<center>
<table style="border-collapse: collapse;" width="1100px">
<tr>
<td width="190px" style="border: 1px solid black;" valign="top">
<center><b>[ Turbine State ]</b></center><br />
<div id="div_status_manual" style="border-radius: 5px; border: 1px solid black; display: inline;background-color: red;" width="25px">&nbsp; &nbsp; &nbsp; &nbsp;</div> Manual<br /><br />
<div id="div_status_auto" style="border-radius: 5px; border: 1px solid black; display: inline; background-color: red;" width="25px">&nbsp; &nbsp; &nbsp; &nbsp;</div> Auto<br /> <br />
<div id="div_status" style="text-align: center;">
    <img src="pics/run.png" id="status_img_run" style="display: none" width="25px" height="25px">
    <img src="pics/stop.png" id="status_img_stop" style="display: none" width="25px" height="25px"><br />
    <img src="pics/warning.png" id="status_img_warning" style="display: none" width="25px" height="25px">
    <span id="warning_text"></span>
    <!-- Broken -->
    <div id="status_error" style="display: none">
        <img src="pics/error.png" id="status_img_error" style="display: none; animation: blink 1s infinite;" width="25px" height="25px">
        <br /><b>!!! BROKEN !!!</b>
    </div>
    <br /><br />
</div>
<center><b>[ Operator ]</b></center><br />
<center>
<input style="text-align: center" onclick="manualStart()" type="button" id="button_start" value="START" disabled><br />
<div id="maintenance_msg" style="display: none; color: red; font-weight: bold; margin-top: 5px;">MAINTENANCE EN COURS</div>
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
<table style="border-collapse: collapse; height: 576px;" width="100%">
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
<td width="200px" style="border: 1px solid black; text-align: center; vertical-align: top;">
    <center><b>[ Ascenseur ]</b></center><br />
    <div id="div_maintenance_auth" style="border: 1px solid black; padding: 3px; margin: 3px; font-weight: bold; background-color: red; color: white;">MAINTENANCE INTERDITE</div>
    <div id="div_nacelle_broken" style="display: none; border: 1px solid black; padding: 3px; margin: 3px; font-weight: bold; background-color: #cc0000; color: white;">NACELLE CASSÉE</div>

    <!-- Schéma SVG ascenseur -->
    <svg width="180" height="300" style="border: 1px solid #ccc; background: #fafafa;">
        <!-- Rail vertical -->
        <rect x="80" y="10" width="20" height="280" fill="none" stroke="black" stroke-width="2"/>
        <!-- Capteur haute -->
        <rect x="70" y="10" width="10" height="10" id="ascenseur_sensor_high" fill="#666666"/>
        <text x="60" y="18" font-size="8" text-anchor="end">H</text>
        <!-- Capteur basse -->
        <rect x="70" y="280" width="10" height="10" id="ascenseur_sensor_low" fill="#666666"/>
        <text x="60" y="288" font-size="8" text-anchor="end">B</text>
        <!-- Cabine mobile (ensemble cabine + Nacelle + porte) -->
        <g id="ascenseur_cabine_g">
            <rect x="75" y="250" width="30" height="40" fill="#ffcc00" stroke="black" stroke-width="1" id="ascenseur_cabine"/>
            <text x="90" y="270" font-size="10" text-anchor="middle">Nacelle</text>
            <rect x="105" y="250" width="8" height="40" fill="#ff6600" id="ascenseur_door" stroke="black" stroke-width="0.5"/>
        </g>
        <!-- Position -->
        <text x="90" y="300" font-size="9" text-anchor="middle" id="ascenseur_position_text">0%</text>
    </svg>

    <!-- Données ascenseur -->
    <table style="width: 100%; font-size: 11px; margin-top: 5px;">
        <tr><td align="left">État:</td><td align="right"><b id="ascenseur_state" style="color: gray;">-</b></td></tr>
        <tr><td align="left">Vitesse:</td><td align="right"><b id="ascenseur_speed">0.0 m/s</b></td></tr>
    </table>

    <!-- Boutons -->
    <div style="margin-top: 8px;">
        <input class="ascenseur_btn" type="button" value="Monter" onclick="sendAscenseurCommand('up')" disabled>
        <input class="ascenseur_btn" type="button" value="Descendre" onclick="sendAscenseurCommand('down')" disabled><br />
        <input class="ascenseur_btn" type="button" value="Arrêt" onclick="sendAscenseurCommand('stop')" disabled>
    </div>
</td>
</tr>
</table>
</center>

</body>
</html>
