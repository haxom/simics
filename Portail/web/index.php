<?php /* 	SCADA - Portail : IHM.
		La dynamique (équations moteur, intégration GAP, registres) reste
		entièrement portée par portail_process.py + modbusactions.php :
		cette page ne fait qu'afficher et envoyer des boutons. */ ?>
<!DOCTYPE html>
<html>
<head>
	<title>SCADA - Portail</title>
	<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
	<link rel="stylesheet" href="css/garage.css" >
	<script>
		var inFlight = false;       /* une seule requête modbusactions.php à la fois */
		var queuedAction = null;    /* clic arrivé pendant une requête en vol  */
		var boom = false;
		var DOOR_H = 309;           /* hauteur CSS de .door-cell (ratio
		                               batmobile.jpg 450x248 à 560px) */

		function displayValues(values)
		{
			if(!values || values.length < 10)
				return;
			var ids = ['CAPT1', 'CAPT2', 'M_UP', 'M_DOWN', 'C_UP', 'C_DOWN',
			           'C_STOP', 'LIGHT1', 'LIGHT2'];
			for(var i = 0; i < ids.length; i++)
				document.getElementById(ids[i]).value = values[i];

			var gap = parseInt(values[9], 10);
			if (isNaN(gap)) gap = 0;
			var gapEl = document.getElementById('GAP');   /* ligne GAP retirée du tableau : garde tolérante si l'input revient */
			if (gapEl) gapEl.value = gap;
			var legend = document.getElementById('GAP_legend');
			if (legend) legend.textContent = Math.max(0, Math.min(gap, 100));
			document.getElementById('bar_fill').style.width = Math.max(0, Math.min(gap, 100)) + '%';

			/* graphisme */
			set({'img_on_light1': (values[0] == 1), 'img_off_light1': (values[0] != 1),
			     'img_on_light2': (values[1] == 1), 'img_off_light2': (values[1] != 1),
			     'img_m_up':      (values[2] == 1), 'img_m_down':      (values[3] == 1)});

			/* porte : même loi linéaire que l'IHM origine, généralisée :
			   fermé (GAP=0) -> hauteur DOOR_H, ouvert (GAP=100) -> 0 */
			document.getElementById('div_gap').style.height =
				(DOOR_H - (DOOR_H/100) * Math.max(0, Math.min(gap, 100))) + 'px';

			boom = (gap > 100 || gap < 0);
			applyBoom(gap);

			document.getElementById('state').className = 'state ' + stateClass(values, gap);
			document.getElementById('state_txt').textContent = stateText(values, gap);
		}

		function set(map)
		{
			for(var id in map)
			{
				var el = document.getElementById(id);
				if(el) el.style.display = map[id] ? 'inline' : 'none';
			}
		}

		function stateClass(values, gap)
		{
			if(boom)                    return 'st_boom';
			if(values[2] == 1)          return 'st_moving';
			if(values[3] == 1)          return 'st_moving';
			if(gap >= 100)              return 'st_open';
			if(gap <= 0)                return 'st_closed';
			return 'st_stopped';
		}

		function stateText(values, gap)
		{
			if(boom)                    return 'MOTEUR CASSÉ';
			if(values[2] == 1)          return 'OUVERTURE...';
			if(values[3] == 1)          return 'FERMETURE...';
			if(gap >= 100)              return 'OUVERT';
			if(gap <= 0)                return 'FERMÉ';
			return 'ARRÊTÉ';
		}

		function applyBoom(gap)
		{
			var motor = document.getElementById('moteur');
			motor.src = boom ? 'boom.jpg' : 'moteur.png';

			/* bannière : plus lisible que le seul swap d'image */
			document.getElementById('boom_banner').style.display = boom ? 'block' : 'none';

			/* commandes coupées tant que le moteur est cassé */
			var ctl = ['btn_up', 'btn_stop', 'btn_down'];
			for(var i = 0; i < ctl.length; i++)
				document.getElementById(ctl[i]).disabled = boom;
		}

		function actionRequest(action)
		{
			if(action)
				optimistic(action);          /* feedback immédiat au clic */
			if(inFlight)
			{
				queuedAction = action;      /* jouée dès la fin de la requête en cours */
				return;
			}
			inFlight = true;
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function()
			{
				if(this.readyState == XMLHttpRequest.DONE)
				{
					inFlight = false;
					var text = this.responseText;
					if(this.status == 200 && text && text.split(':').length >= 10)
						displayValues(text.split(':'));
					else
						showModbusError();   /* jamais de no-op silencieux */
					if(queuedAction)
					{
						var next = queuedAction;
						queuedAction = null;
						actionRequest(next);
					}
				}
			}
			xhr.onerror = function() { inFlight = false; queuedAction = null; showModbusError(); };
			/* cache-buster : chaque poll doit repartir au serveur */
			var url = 'modbusactions.php' + (action ? ('?action=' + action) : '');
			url += ((url.indexOf('?') >= 0) ? '&' : '?') + 't=' + Date.now();
			xhr.open('GET', url, true);
			xhr.send();
		}

		function showModbusError()
		{
			/* réponse non conforme / serveur absent : état explicite plutôt
			   que « rien ne se passe » (ex. modbusactions.php pas rebuilt) */
			var st = document.getElementById('state');
			st.className = 'state st_error';
			document.getElementById('state_txt').textContent = 'MODBUS ERREUR';
		}

		function optimistic(action)
		{
			/* retour visuel immédiat au clic, avant confirmation serveur
			   (le premier pas physique attend le prochain cycle process) */
			var st = document.getElementById('state');
			if(boom || action == 'reset')
				return;
			if(action == 'C_UP')
			{
				st.className = 'state st_moving';
				document.getElementById('state_txt').textContent = 'OUVERTURE...';
				set({'img_m_up': true, 'img_m_down': false});
			}
			else if(action == 'C_DOWN')
			{
				st.className = 'state st_moving';
				document.getElementById('state_txt').textContent = 'FERMETURE...';
				set({'img_m_down': true, 'img_m_up': false});
			}
			else if(action == 'C_STOP')
			{
				st.className = 'state st_stopped';
				document.getElementById('state_txt').textContent = 'ARRÊT...';
				set({'img_m_up': false, 'img_m_down': false});
			}
		}
	</script>
</head>
<body>
<nav class='topbar'>SCADA - Portail <span class="sub">simulation TurboElec</span></nav>

<div class='layout'>
	<!-- Porte : même mécanique que l'ancienne IHM
	     (div_gap = DOOR_H - DOOR_H/100 * GAP, DOOR_H = 309) -->
	<div class='panel scene'>
		<div class='scene-top'>
			<span class='sensor led'>
				<img src='light_on.jpg'  id='img_on_light1'  width='30' height='30' alt='LIGHT1' style='display:none'>
				<img src='light_off.png' id='img_off_light1' width='30' height='30' alt='LIGHT1'>
				<img src='laser.jpg' width='30' height='30' title='CAPT1'>
			</span>
			<span></span>
			<span><img id='moteur' src='moteur.png' width='50' height='50' alt='moteur'></span>
		</div>
		<div class='scene-mid'>
			<span></span>
			<div class='door-cell'>
				<div id='div_gap'></div>
			</div>
			<span class='arrows'>
				<img id='img_m_up'   src='m_up.gif'   width='30' height='30' alt='M_UP'   style='display:none'><br>
				<img id='img_m_down' src='m_down.gif' width='30' height='30' alt='M_DOWN' style='display:none'>
			</span>
		</div>
		<div class='scene-bottom'>
			<span class='sensor led'>
				<img src='light_on.jpg'  id='img_on_light2'  width='30' height='30' alt='LIGHT2' style='display:none'>
				<img src='light_off.png' id='img_off_light2' width='30' height='30' alt='LIGHT2'>
				<img src='laser.jpg' width='30' height='30' title='CAPT2'>
			</span>
			<span></span>
			<span></span>
		</div>
	</div>

	<!-- Colonne droite : commandes puis registres -->
	<div class='side'>
		<!-- Commandes + état -->
		<div class='panel'>
			<div id='boom_banner' class='boom' style='display:none'>
				<b>MOTEUR CASSÉ</b> — le portail ne peut plus bouger.
			</div>

			<div id='state' class='state st_stopped'><span id='state_txt'>CONNEXION...</span></div>

			<div class='ctl'>
				<input type='button' class='big up'      id='btn_up'    value='▲ OUVRIR'        onclick="actionRequest('C_UP')">
				<input type='button' class='big stop'    id='btn_stop'  value='■ ARRÊT'         onclick="actionRequest('C_STOP')">
				<input type='button' class='big down'    id='btn_down'  value='▼ FERMER'        onclick="actionRequest('C_DOWN')">
			</div>

			<div class='bar'><div id='bar_fill' style='width:0%'></div></div>
			<div class='legend'>ouverture <b id='GAP_legend'>0</b> %</div>

			<!-- reset TOUJOURS discret : petit bouton fantôme, coin bas du panneau -->
			<div class='resetrow'>
				<button id='btn_reset' class='ghost' title="remet le portail à zéro (GAP et entrées)"
						onclick="actionRequest('reset')">réinitialiser</button>
			</div>
		</div>

		<!-- Registres Modbus : VISIBLES en permanence, sous les boutons -->
		<div class='panel dbg'>
			<h3>Registres Modbus (unité 45 / 0x2d)</h3>
			<table class='registers'>
				<tr><th>Reg</th><th>Name</th><th></th></tr>
				<tr><td>0x00</td><td class='input'>CAPT1</td><td><input id="CAPT1" value="0" readonly></td></tr>
				<tr><td>0x01</td><td class='input'>CAPT2</td><td><input id="CAPT2" value="0" readonly></td></tr>
				<tr><td>0x02</td><td class='io'>M_UP</td><td><input id="M_UP"  value="0" readonly></td></tr>
				<tr><td>0x03</td><td class='io'>M_DOWN</td><td><input id="M_DOWN" value="0" readonly></td></tr>
				<tr><td>0x04</td><td class='input'>C_UP</td><td><input id="C_UP" value="0" readonly></td></tr>
				<tr><td>0x05</td><td class='input'>C_DOWN</td><td><input id="C_DOWN" value="0" readonly></td></tr>
				<tr><td>0x06</td><td class='input'>C_STOP</td><td><input id="C_STOP" value="0" readonly></td></tr>
				<tr><td>0x07</td><td class='output'>LIGHT1</td><td><input id="LIGHT1" value="0" readonly></td></tr>
				<tr><td>0x08</td><td class='output'>LIGHT2</td><td><input id="LIGHT2" value="0" readonly></td></tr>
			</table>
		</div>
	</div>
</div>

	<!-- Montrer les process : SOUS tout, sur la largeur -->
<div class='bottom-row'>
	<details class='panel dbg proc'>
		<summary>Montrer les process</summary>
		<table class='processes'>
			<tr><th>Process :</th></tr>
			<tr><td>LIGHT1 = CAPT1</td></tr>
			<tr><td>LIGHT2 = CAPT2</td></tr>
			<tr><td>M_UP = (not M_DOWN) and (not CAPT1) and (not C_STOP) and (C_UP or M_UP)</td></tr>
			<tr><td>M_DOWN = (not M_UP) and (CAPT2) and (not C_STOP) and (C_DOWN or M_DOWN)</td></tr>
		</table>
	</details>
</div>

<script>
	/* Répétition 4x/s : la simulation avance par pas de 3 et le process
	   commande à 5 Hz, un poll de 250 ms suit la physique de près
	   (une seule requête à la fois, les clics pendant un poll
	   s'enregistrent juste après) */
	actionRequest(null);
	setInterval(function(){ actionRequest(null); }, 250);
</script>

</body>
</html>
