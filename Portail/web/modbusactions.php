<?php
	$action = False;
	if(isset($_GET['action']) && !empty($_GET['action']))
		$action = $_GET['action'];

	$CAPT1 = 0;
	$CAPT2 = 0;
	$M_UP = 0;
	$M_DOWN = 0;
	$C_UP = 0;
	$C_DOWN = 0;
	$C_STOP = 0;
	$LIGHT1 = 0;
	$LIGHT2 = 0;
	$GAP = 0;

	require_once 'phpmodbus/Phpmodbus/ModbusMaster.php';
	$modbus = new ModbusMaster('127.0.0.1', 'TCP');
	
	// read registers
	$CAPT1 = $modbus->readMultipleRegisters(45, 0, 1)[1];
	$CAPT2 = $modbus->readMultipleRegisters(45, 1, 1)[1];
	$M_UP = $modbus->readMultipleRegisters(45, 2, 1)[1];
	$M_DOWN = $modbus->readMultipleRegisters(45, 3, 1)[1];
	$C_UP = $modbus->readMultipleRegisters(45, 4, 1)[1];
	$C_DOWN = $modbus->readMultipleRegisters(45, 5, 1)[1];
	$C_STOP = $modbus->readMultipleRegisters(45, 6, 1)[1];
	$LIGHT1 = $modbus->readMultipleRegisters(45, 7, 1)[1];
	$LIGHT2 = $modbus->readMultipleRegisters(45, 8, 1)[1];

	$GAP = intval(value: file_get_contents(filename: 'hauteur.txt', use_include_path: false, context: NULL, offset: 0, length: 3));
	//if($GAP > 100 or $GAP < 0)
	//	$GAP = 100;

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
		}
	}

	// update $H
	if($M_UP)
		$GAP += 5;
	if($M_DOWN)
		$GAP -= 5;

	// update captors
	$CAPT1 = 0;
	$CAPT2 = 0;
	if($GAP >= 100)
		$CAPT1 = 1;
	if($GAP > 0)
		$CAPT2 = 1;

	// save registers
	$data_type = array('INT');
	$modbus->writeMultipleRegister(45, 0, array($CAPT1), $data_type);
	$modbus->writeMultipleRegister(45, 1, array($CAPT2), $data_type);
	$modbus->writeMultipleRegister(45, 4, array($C_UP), $data_type);
	$modbus->writeMultipleRegister(45, 5, array($C_DOWN), $data_type);
	$modbus->writeMultipleRegister(45, 6, array($C_STOP), $data_type);

	file_put_contents(filename: 'hauteur.txt', data: $GAP);

	echo $CAPT1.':'.$CAPT2.':'.	$M_UP.':'.$M_DOWN.':'.$C_UP.':'.$C_DOWN.':'.$C_STOP.':'.$LIGHT1.':'.$LIGHT2.':'.$GAP;
