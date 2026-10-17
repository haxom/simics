<?php
	/* Anti-cache : les polls XHR doivent toujours repartir au serveur
	   (sinon un GET caché donne un IHM figée / un reset mutique). */
	header('Cache-Control: no-store, no-cache, must-revalidate');
	header('Pragma: no-cache');

	/*
	 * SCADA - Portail : un appel = un pas de la simulation.
	 *
	 * Sémantique inchangée (mêmes registres unité 45/0x2d, mêmes équations,
	 * même hauteur.txt) — l'IHM moderne repose dessus :
	 *   - lecture GROUPÉE : les 9 registres 0..8 sont contigus, une seule
	 *     requête Modbus au lieu de 9 sockets phpmodbus par appel ;
	 *   - écritures groupées : CAPT1/CAPT2 (0..1) et boutons C_* (4..6) ;
	 *   - flock() sur hauteur.txt : l'intégration du GAP est atomique, un
	 *     poll et un clic ne peuvent plus se superposer (fin des doubles
	 *     pas qui sortaient le moteur de ses bornes).
	 *
	 * Action supplémentaire côté IHM (pas du process) : `reset` remet le
	 * GAP et les registres d'entrée à zéro (équivalent IHM du docker
	 * restart, pour un nouveau tour après un « moteur cassé »).
	 */

	$action = False;
	if(isset($_GET['action']) && !empty($_GET['action']))
		$action = $_GET['action'];
	if($action !== False && !in_array($action, array('C_UP', 'C_DOWN', 'C_STOP', 'reset'), true))
		$action = False;

	/* Pas d'intégration du GAP par cycle (un cycle = un poll de 250 ms) :
	   3 -> ~12 %/s, porte complète en ~8 s (l'ancien pas de 5 donnait
	   20 %/s, jugé trop rapide). Le clamp min/max reste obligatoire :
	   99 + 3 = 102 est rabattu à 100, CAPT1 se déclenche comme avant. */
	$STEP = 3;

	require_once 'phpmodbus/Phpmodbus/ModbusMaster.php';
	$modbus = new ModbusMaster('127.0.0.1', 'TCP');

	// lecture groupée : CAPT1, CAPT2, M_UP, M_DOWN, C_UP, C_DOWN, C_STOP,
	// LIGHT1, LIGHT2 (registres 0..8 contigus, 2 octets par valeur)
	$bytes = $modbus->readMultipleRegisters(45, 0, 9);
	$values = array();
	for($i = 0; $i < 9; $i++)
		$values[$i] = $bytes[2*$i + 1];   // LSB, comme readMultipleRegister(.., 1)[1]

	list($CAPT1, $CAPT2, $M_UP, $M_DOWN, $C_UP, $C_DOWN, $C_STOP, $LIGHT1, $LIGHT2) = $values;

	// action demandée : le bouton reste appuyé le temps de la boucle
	if($action)
	{
		switch($action)
		{
			case 'C_UP':
				$C_UP = 1;
				break;
			case 'C_DOWN':
				$C_DOWN = 1;
				break;
			case 'C_STOP':
				$C_STOP = 1;
				break;
			case 'reset':
				// remise à zéro des entrées ; le GAP suit ci-dessous
				$C_UP = $C_DOWN = $C_STOP = 0;
				break;
		}
	}

	// hauteur.txt : lecture + pas moteur sous verrou (atomique)
	$GAP = 0;
	$fp = @fopen('hauteur.txt', 'c+');
	if($fp !== false && flock($fp, LOCK_EX))
	{
		$GAP = (int)trim((string)fread($fp, 3));

		if($action == 'reset')
			$GAP = 0;

		// intégration moteur : MÊMES équations que le process, mais pas
		// BORNÉ : le verrou M_UP/M_DOWN lu dans les registres peut dater
		// d'avant le pas précédent (le process tourne à 5 Hz, le poll à
		// 250 ms). Sans bornes, un verrou périmé d'un cycle faisait
		// déborder le GAP : « moteur cassé » spontané en arrivant en
		// haut/en bas. La casse reste possible si hauteur.txt est altéré
		// à la main (docker exec...) — c'est un garde-fou, plus une pièce
		// du scénario.
		if($M_UP)
			$GAP = min($GAP + $STEP, 100);
		if($M_DOWN)
			$GAP = max($GAP - $STEP, 0);

		ftruncate($fp, 0);
		rewind($fp);
		fwrite($fp, (string)$GAP);
		fflush($fp);
		flock($fp, LOCK_UN);
		fclose($fp);
	}

	// update captors (dérivés du GAP, comme avant)
	$CAPT1 = 0;
	$CAPT2 = 0;
	if($GAP >= 100)
		$CAPT1 = 1;
	if($GAP > 0)
		$CAPT2 = 1;

	// save registers : écritures groupées (jamais 2/3 : le process
	// M_UP/M_DOWN leur appartient)
	$data_type = array('INT', 'INT');
	$modbus->writeMultipleRegister(45, 0, array($CAPT1, $CAPT2), $data_type);
	$modbus->writeMultipleRegister(45, 4, array($C_UP, $C_DOWN, $C_STOP),
		array('INT', 'INT', 'INT'));

	// reset : on coupe AUSSI le moteur (registres 2/3). Ce sont des
	// registres process (verrou "C_UP or M_UP") qu'on ne touche jamais
	// dans le poll normal — mais un reset doit tuer le verrou, sinon le
	// process se relatche et la porte repart toute seule.
	if($action == 'reset')
	{
		$modbus->writeMultipleRegister(45, 2, array(0, 0), array('INT', 'INT'));
		$M_UP = 0;        // écho immédiat à l'IHM (le poll suivant confirme)
		$M_DOWN = 0;
	}

	echo $CAPT1.':'.$CAPT2.':'.$M_UP.':'.$M_DOWN.':'.$C_UP.':'.$C_DOWN.':'.$C_STOP.':'.$LIGHT1.':'.$LIGHT2.':'.$GAP;
