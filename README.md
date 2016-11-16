### Description:
---

This is a service (task) for [VolgaCTF 2016 Quals](https://volgactf.ru/) competition.

Web socket chat application on tornado engine.

With injection into NoSQL MongoDB vulnerability.
You need to recive message from bot from VolgaCTF_Flag_Channel.

Use it for education purposes only.


application use:

	mongodb = 3.2.4
	
	python = 3.5



injection vectors

	#'}), db.connections.save({'token':'123'})}//
	#'}), db.connections.save({"token": "ca434f43e33ccf546a765742f60ec7ec", "channel_id": "56f442972b03a12728a9ff55"})}//
