<html>
	<head>
		<title>SCADA - Portail</title>
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />

		<link rel="stylesheet" href="css/bootstrap.min.css" >
		<link rel="stylesheet" href="css/garage.css"        >

		<script>

				function displayValues(values)
				{
					document.getElementById("CAPT1").value  = values[0];
					document.getElementById("CAPT2").value  = values[1];
					document.getElementById("M_UP").value   = values[2];
					document.getElementById("M_DOWN").value = values[3];
					document.getElementById("C_UP").value   = values[4];
					document.getElementById("C_DOWN").value = values[5];
					document.getElementById("C_STOP").value = values[6];
					document.getElementById("LIGHT1").value = values[7];
					document.getElementById("LIGHT2").value = values[8];
					document.getElementById("GAP").value    = values[9];

					if(values[0] == 1)
					{
						document.getElementById('img_on_light1').style.display  = 'inline';
						document.getElementById('img_off_light1').style.display = 'none';
					}
					else
					{
						document.getElementById('img_on_light1').style.display  = 'none';
						document.getElementById('img_off_light1').style.display = 'inline';
					}

					if(values[1] == 1)
					{
						document.getElementById('img_on_light2').style.display  = 'inline';
						document.getElementById('img_off_light2').style.display = 'none';
					}
					else
					{
						document.getElementById('img_on_light2').style.display  = 'none';
						document.getElementById('img_off_light2').style.display = 'inline';
					}

					if(values[2] == 1)
						document.getElementById('img_m_up').style.display = 'inline';
					else
						document.getElementById('img_m_up').style.display = 'none';

					if(values[3] == 1)
						document.getElementById('img_m_down').style.display = 'inline';
					else
						document.getElementById('img_m_down').style.display = 'none';

					document.getElementById('div_gap').style.height = 300-3*values[9];
					if(values[9] > 100 || values[9] < 0)
						document.getElementById('moteur').src = 'boom.jpg';
				}

				function renewValues()
				{
					var xmlhttp = new XMLHttpRequest();
					xmlhttp.onreadystatechange = function()
					{
						if(xmlhttp.readyState == 4)
							displayValues(xmlhttp.responseText.split(':'));
					}
					xmlhttp.open('GET', 'modbusactions.php', true);
					xmlhttp.send();
				}

				function trigAction(action)
				{
					var xmlhttp = new XMLHttpRequest();
					xmlhttp.onreadystatechange = function()
					{
						if(xmlhttp.readyState == 4)
							diplayValues(xmlhttp.responseText.split(':'));
					}
					xmlhttp.open('GET', 'modbusactions.php?action='+action, true);
					xmlhttp.send();
				}
		</script>
	</head>
	<body onload='setInterval("renewValues()", 1000)' class='application'>
<nav class='navbar navbar-default navbar-fixed-top' role='navigation'>
	<div class='container-fluid'>
		<div class='navbar-header'>
			<a class='navbar-brand' id='brand' href='#'>Garage control</a>
		</div>
	</div>
</nav>
<div class='container'>
<table class='door'>
 <tr height="5">
  <td width="10%" align="center"><img height="30" width="30" src='light_on.jpg' style='display:none' id='img_on_light1' alt="LIGHT1" /><img height="30" width="30" src='light_off.png' style='display:none' id='img_off_light1' alt='LIGHT1' /> <img height="30" width="30" src="laser.jpg" alt="CAPT1" /></td>
  <td width="80%"></td>
  <td width="10%" align="center"><img src="moteur.png" id='moteur' width="50" height="50"></td>
 </tr>
 <tr height="300">
  <td></td>
  <td valign="top" align="center" style="background-color: black; background-image: url('batmobile.jpg');background-repeat:no-repeat;background-position:center center;">
   <div id='div_gap' style='background-image: url("portail.jpg");height=300;border=1' widht='100%'></div>
  </td>
  <td align="center"><img height="30" width="30" src='m_up.gif' id='img_m_up' alt='M_UP' style='display:none'><br /><img height="30" width="30" src='m_down.gif' id='img_m_down' alt='M_DOWN' style='display:none'></td>
 </tr>
 <tr height="5">
  <td  valign="top" align="center"><img height="30" width="30" src='light_on.jpg' style='display:none' id='img_on_light2' alt="LIGHT2" /><img height="30" width="30" src='light_off.png' style='display:none' id='img_off_light2' alt='LIGHT2' /> <img height="30" width="30" src="laser.jpg" alt="CAPT2" /></td>
  <td></td>
  <td></td>
 </tr>
</table>
<br>
<div class='registers' >
	<table class='registers'>
		<tr><th colspan='3'> Raw Values : </th></tr>
		<tr>
			<td class='code'>0x00</td>
			<td class='input'>CAPT1</td>
			<td><input id="CAPT1" value="0" ></td>
		</tr>
		<tr>
			<td class='code'>0x01</td>
			<td class='input'>CAPT2</td>
			<td><input id="CAPT2" value="0" ></td>
		</tr>
		<tr>
			<td class='code'>0x02</td>
			<td class='io'>M_UP</td>
			<td><input id="M_UP"  value="0" ></td>
		</tr>
		<tr>
			<td class='code'>0x03</td>
			<td class='io'>M_DOWN</td>
			<td><input id="M_DOWN" value="0" ></td>
		</tr>
		<tr>
			<td class='code'>0x04</td>
			<td class='input'>C_UP</td>
			<td><input id="C_UP" value="0" >
				<button  value="C_UP" 
						 onclick="trigAction('C_UP')" 
						 class='btn btn-sm btn-default'>
				C_UP
				</button>
			</td>
		</tr>
		<tr>
			<td class='code'>0x05</td>
			<td class='input'>C_DOWN</td>
			<td><input id="C_DOWN" value="0" > 
				<button	value="C_DOWN" 
						onclick="trigAction('C_DOWN')" 
						class='btn btn-sm btn-default'>
				C_DOWN
				</button>
			</td>
		</tr>
		<tr>
			<td class='code'>0x06</td>
			<td class='input'>C_STOP</td>
			<td>
				<input id="C_STOP" value="0" > 
				<button value="C_STOP" 
						onclick="trigAction('C_STOP')" 
						class='btn btn-sm btn-default'>
				C_STOP
				</button>
			</td>
		</tr>
		<tr>
			<td class='code'>0x07</td>
			<td class='output'>LIGHT1</td>
			<td>
				<input id="LIGHT1" value="0" >
			</td>
		</tr>
		<tr>
			<td class='code'>0x08</td>
			<td class='output'>LIGHT2</td>
			<td>
				<input id="LIGHT2" value="0" >
			</td>
		</tr>
		<tr>
			<td class='code'>XxXX</td>
			<td>GAP</td>
			<td>
				<input id="GAP" value="0" >
			</td>
		</tr>
	</table>
</div>
<br>
<a href="#" onclick="document.getElementById('processes').style='inline';">Montrer les process</a>
<div class='processes' id='processes' style='display:none'>
	<table class='processes'>			
			<tr>
				<th>Processes :</th>
			</tr>
			<tr><td>LIGHT1 = CAPT1</td></tr>
			<tr><td>LIGHT2 = CAPT2</td></tr>
			<tr><td>M_UP = (not M_DOWN) and (not CAPT1) and (not C_STOP) and (C_UP or M_UP)</td></tr>
			<tr><td>M_DOWN = (not M_UP) and (CAPT2) and (not C_STOP) and (C_DOWN or M_DOWN)</td></tr>
		</tr>
	</table>
</div>
<br><br>

</div><!-- eo container -->

</body>
</html>
