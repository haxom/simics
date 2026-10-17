<?php
	/*
	 * Pare-feu local de l'éolienne : page de gestion des règles iptables.
	 * @version 1.0
	 *
	 * Relais vers l'API locale (process/firewall_api.py sur 127.0.0.1:8081),
	 * comme la page principale relaie l'API ascenseur : le navigateur du
	 * stagiaire ne peut pas joindre le loopback du conteneur.
	 *
	 * Page volontairement sans authentification (exercice défensif) : le
	 * stagiaire trouve cette page et construit ses règles de filtrage.
	 */

	$api_base = 'http://127.0.0.1:8081';

	// --- Relais des actions (POST) : firewall.php?a=rules|delete|reset|capture/start|capture/stop ---
	if($_SERVER['REQUEST_METHOD'] === 'POST')
	{
		header('Content-Type: application/json');
		$api_action = isset($_GET['a']) ? $_GET['a'] : '';
		if(!in_array($api_action, array('rules', 'delete', 'reset',
				'capture/start', 'capture/stop'), true))
		{
			http_response_code(400);
			print json_encode(array('error' => 'invalid action'));
			exit();
		}
		$ctx = stream_context_create(array('http' => array(
			'method'  => 'POST',
			'header'  => "Content-Type: application/json\r\n",
			// corps JSON relais tel quel : validation côté API python
			'content' => (string)file_get_contents('php://input'),
			// 5 s : capture_stop attend jusqu'à 5 s le flush du PCAP
			'timeout' => 5,
			// les erreurs métier de l'API (validation, règle interdite
			// sur le port 80...) arrivent en HTTP 400 avec un corps
			// JSON fonctionnel : il doit être relayé tel quel
			'ignore_errors' => true,
		)));
		$response = @file_get_contents($api_base . '/api/' . $api_action, false, $ctx);
		if($response === false)
		{
			http_response_code(502);
			print json_encode(array('error' => 'firewall api unavailable'));
		}
		else
		{
			print $response;
		}
		exit();
	}

	// --- Relais des lectures (poll du JS) : firewall.php?act=read|cap_state ---
	if(isset($_GET['act']) && ($_GET['act'] === 'read' || $_GET['act'] === 'cap_state'))
	{
		header('Content-Type: application/json');
		$api_path = ($_GET['act'] === 'cap_state') ? '/api/capture/state' : '/api/rules';
		$ctx = stream_context_create(array('http' => array(
			'timeout' => 2,
			'ignore_errors' => true,
		)));
		$response = @file_get_contents($api_base . $api_path, false, $ctx);
		if($response === false)
		{
			http_response_code(502);
			print json_encode(array('error' => 'firewall api unavailable'));
		}
		else
		{
			print $response;
		}
		exit();
	}

	// --- Relais du téléchargement de la capture : firewall.php?act=cap_download ---
	if(isset($_GET['act']) && $_GET['act'] === 'cap_download')
	{
		$ctx = stream_context_create(array('http' => array(
			'method' => 'GET',
			'timeout' => 30,
			'ignore_errors' => true,
		)));
		$fp = @fopen($api_base . '/api/capture/download', 'rb', false, $ctx);
		if($fp === false)
		{
			header('Content-Type: application/json');
			http_response_code(502);
			print json_encode(array('error' => 'firewall api unavailable'));
			exit();
		}
		// statut et longueur communiqués par l'API via $http_response_header
		$status = 0;
		$length = null;
		foreach($http_response_header as $h)
		{
			if(preg_match('#^HTTP/\S+ (\d+)#', $h, $m))
				$status = (int)$m[1];
			if(stripos($h, 'content-length:') === 0)
				$length = trim(substr($h, 15));
		}
		if($status !== 200)
		{
			// corps d'erreur JSON de l'API relayé tel quel : 409 « capture
			// en cours », 404 « aucune capture disponible »...
			$body = @stream_get_contents($fp);
			fclose($fp);
			header('Content-Type: application/json');
			http_response_code($status >= 400 ? $status : 502);
			if($body !== false && json_decode($body, true) !== null)
				print $body;
			else
				print json_encode(array('error' => 'capture indisponible'));
			exit();
		}
		header('Content-Type: application/vnd.tcpdump.pcap');
		header('Content-Disposition: attachment; filename="turboelec_capture.pcap"');
		if($length !== null)
			header('Content-Length: ' . $length);
		fpassthru($fp);
		fclose($fp);
		exit();
	}
?>
<!DOCTYPE html>
<html>
<head>
	<meta charset="utf-8">
	<title>TURBOElec - Pare-feu local</title>
	<style>
		body { font-family: Arial, Helvetica, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }
		h1 { text-align: center; font-size: 20px; margin: 5px 0 15px; }
		h2 { font-size: 15px; margin: 15px 0 8px; }
		#app { max-width: 960px; margin: 0 auto; }

		.form_zone, .rules_zone {
			background: #fff; border: 1px solid #ccc; border-radius: 8px;
			padding: 10px 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
		}
		label { font-size: 13px; }
		fieldset { border: 1px solid #ddd; border-radius: 5px; margin: 5px 0; }
		input[type=text], input[type=number], select { padding: 3px 6px; margin: 2px 0; }

		.rules_zone table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
		.rules_zone th, .rules_zone td { border: 1px solid #bbb; padding: 3px 6px; text-align: center; }
		.rules_zone th { background: #eee; }

		.act_drop { color: #c9302c; font-weight: bold; }
		.act_reject { color: #e08b1a; font-weight: bold; }
		.act_accept { color: #2e9e34; font-weight: bold; }

		#status { color: #555; font-size: 12.5px; min-height: 18px; }
		.btn_delete { font-size: 11px; padding: 1px 7px; cursor: pointer; }
		.error { color: #c9302c; font-weight: bold; font-size: 12.5px; }
	</style>
	<script>
		var rules = {"in": [], "out": []};
		var polling = false;

		function addRule()
		{
			var direction = document.querySelector('input[name=direction]:checked').value;
			var action = document.getElementById('f_action').value;
			var proto = document.getElementById('f_proto').value;
			var ip = document.getElementById('f_ip').value.trim();
			var port = document.getElementById('f_port').value.trim();
			var error = document.getElementById('form_error');

			error.textContent = "";
			document.getElementById('status').textContent = "";

			var payload = { "direction": direction, "action": action, "proto": proto };
			if(ip != "")
				payload["ip"] = ip;
			if(port != "")
				payload["port"] = port;

			apiPost('rules', payload);
		}

		function deleteRule(direction, index)
		{
			apiPost('delete', { "direction": direction, "index": index });
		}

		function resetRules()
		{
			if(!confirm("Supprimer toutes les règles du pare-feu local ?"))
				return;
			apiPost('reset', {});
		}

		function apiPost(action, payload)
		{
			var xhr = new XMLHttpRequest();
			xhr.onerror = function() { document.getElementById('status').textContent = "Pare-feu injoignable"; };
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					var response = null;
					try { response = JSON.parse(this.responseText); } catch(e) {}
					if(this.status == 200 && response && response.ok)
					{
						document.getElementById('form_error').textContent = "";
						updateData();
						updateCapState();
						return;
					}
					// l'API répond ses erreurs (validation, règle interdite,
					// self-lockout port 80...) en JSON même sur un statut 400 :
					// priorité au message métier explicite
					document.getElementById('form_error').textContent =
						"Erreur : " + ((response && response.error) || ("Échec (HTTP " + this.status + ")"));
				}
			}
			xhr.open('POST', 'firewall.php?a=' + action, true);
			xhr.setRequestHeader('Content-Type', 'application/json');
			xhr.send(JSON.stringify(payload));
		}

		function captureControl(action)
		{
			apiPost('capture/' + action, {});
		}

		function updateCapState()
		{
			var xhr = new XMLHttpRequest();
			xhr.onerror = function() { document.getElementById('cap_status').textContent = ""; };
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					try {
						var state = JSON.parse(this.responseText);
						var size = Math.round((state.size || 0) / 1024);
						var minutes = Math.max(1, Math.ceil((state.remaining || 0) / 60));
						var dl = document.getElementById('cap_dl');
						// le PCAP d'une capture en cours est tronqué (et
						// refusé par l'API) : lien neutralisé en attendant
						if(state.running)
						{
							dl.removeAttribute('href');
							dl.style.pointerEvents = 'none';
							dl.style.opacity = '0.45';
							document.getElementById('cap_status').textContent =
								"Capture en cours (" + size + " Ko) — arrêt "
								+ "automatique dans ~" + minutes + " min";
						}
						else
						{
							if(!dl.getAttribute('href'))
								dl.setAttribute('href', 'firewall.php?act=cap_download');
							dl.style.pointerEvents = 'auto';
							dl.style.opacity = '1';
							document.getElementById('cap_status').textContent =
								size ? "Capture arrêtée — " + size + " Ko au téléchargement"
								     : "Aucune capture disponible";
						}
						document.getElementById('cap_start').disabled = state.running;
						document.getElementById('cap_stop').disabled = !state.running;
					} catch(e) {}
				}
			}
			xhr.open('GET', 'firewall.php?act=cap_state', true);
			xhr.send(null);
		}

		function updateData()
		{
			if(polling)
				return;
			polling = true;
			var xhr = new XMLHttpRequest();
			xhr.onerror = function() { polling = false; document.getElementById('status').textContent = "Pare-feu injoignable"; };
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					polling = false;
					try {
						rules = JSON.parse(this.responseText);
						document.getElementById('status').textContent = "";
						updateView();
					} catch(e) {
						console.error("Réponse firewall invalide :", e);
					}
				}
			}
			xhr.open('GET', 'firewall.php?act=read', true);
			xhr.send(null);
		}

		function updateView()
		{
			var html = "<tr><th>Direction</th><th>#</th><th>Action</th><th>Protocole</th>" +
				"<th>Source</th><th>Destination</th><th>Port</th><th>Paquets</th><th>Octets</th><th></th></tr>";

			var rows = [["out", "sortant"], ["in", "entrant"]];
			var total = 0;
			for(var r=0; r<rows.length; r++)
			{
				var direction = rows[r][0];
				var label = rows[r][1];
				var list = rules[direction] || [];
				for(var i=0; i<list.length; i++)
				{
					var rule = list[i];
					total++;
					var act = rule['action'].toLowerCase();
					var port = "—";
					if(rule['extra'].indexOf("dpt:") >= 0)
						port = rule['extra'].split("dpt:")[1].split(" ")[0];
					else if(rule['extra'].indexOf("spt:") >= 0)
						port = rule['extra'].split("spt:")[1].split(" ")[0];
					html += "<tr>" +
						"<td>" + label + "</td>" +
						"<td>" + rule['index'] + "</td>" +
						"<td class='act_" + act + "'>" + rule['action'] + "</td>" +
						"<td>" + rule['proto'] + "</td>" +
						"<td>" + rule['source'] + "</td>" +
						"<td>" + rule['destination'] + "</td>" +
						"<td>" + (rule['proto'] == 'any' ? "—" : port) + "</td>" +
						"<td>" + rule['pkts'] + "</td>" +
						"<td>" + rule['bytes'] + "</td>" +
						"<td><input class='btn_delete' type='button' value='X' " +
						"onclick=\"deleteRule('" + direction + "'," + rule['index'] + ")\"></td>" +
					"</tr>";
				}
			}
			if(total == 0)
				html += "<tr><td colspan='10'>Aucune règle — le pare-feu ne filtre rien.</td></tr>";

			document.getElementById('rules_table').innerHTML = html;
		}

		setInterval(updateData, 2000);
		updateData();
		setInterval(updateCapState, 2000);
		updateCapState();
	</script>
</head>
<body>
	<h1>TURBOElec - Pare-feu local de l'éolienne</h1>
	<div id="app">

		<div class="form_zone">
			<h2>Ajouter une règle</h2>
			<fieldset style="display:inline-block; margin-right:10px;">
				<legend>Direction</legend>
				<label><input type="radio" name="direction" value="out" checked> Sortant (depuis l'éolienne)</label><br>
				<label><input type="radio" name="direction" value="in"> Entrant (vers l'éolienne)</label>
			</fieldset>
			<fieldset style="display:inline-block; margin-right:10px;">
				<legend>Traffic</legend>
				<label>Action <select id="f_action">
					<option value="DROP" selected>DROP (silencieux)</option>
					<option value="REJECT">REJECT (refus net)</option>
					<option value="ACCEPT">ACCEPT (laisser passer)</option>
				</select></label><br>
				<label>Protocole <select id="f_proto">
					<option value="tcp" selected>TCP</option>
					<option value="udp">UDP</option>
					<option value="any">tout</option>
				</select></label><br>
				<label>Port destination <input type="number" id="f_port" min="1" max="65535" size="6"></label>
			</fieldset>
			<fieldset style="display:inline-block; margin-right:10px;">
				<legend>Adresse (optionnelle)</legend>
				<label>IP <input type="text" id="f_ip" size="16" placeholder="ex. 172.18.0.5"></label><br>
				<small>Direction sortant : IP de destination. Direction entrant : IP source.</small>
			</fieldset>
			<br><br>
			<input type="button" value="Ajouter la règle" onclick="addRule()">
			<input type="button" value="Supprimer toutes les règles" onclick="resetRules()">
			<div class="error" id="status"></div>
			<div class="error" id="form_error"></div>
		</div>

		<div class="form_zone">
			<h2>Capture réseau</h2>
			<p style="font-size:12.5px;color:#555;margin:4px 0 8px;">
				Capture brute sans filtre sur l'interface réseau de l'éolienne (tcpdump),
				à analyser dans Wireshark. Durée maximale : 10 minutes, avec arrêt
				automatique ; le téléchargement du PCAP est possible une fois la
				capture arrêtée.
			</p>
			<input type="button" id="cap_start" value="Démarrer la capture" onclick="captureControl('start')">
			<input type="button" id="cap_stop" value="Arrêter la capture" onclick="captureControl('stop')" style="margin-left:8px;">
			<a id="cap_dl" href="firewall.php?act=cap_download" style="margin-left:12px;">Télécharger le PCAP</a>
			<div id="cap_status" style="margin-top:6px;"></div>
		</div>

		<div class="rules_zone">
			<h2>Règles actives</h2>
			<table id="rules_table"></table>
			<p style="font-size:11.5px;color:#777;margin:4px 0 0;">
				Compteurs iptables : « Paquets » / « Octets » filtrés depuis la création de la règle.
			</p>
		</div>

	</div>
</body>
</html>
