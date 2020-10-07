import asyncio
from qcluster.communication import HTTPCommunicator


class QCluster(object):
    def __init__(self,
                 identifier,
                 listen_port,
                 listen_host='localhost',
                 peers=[]):
        self.identifier = identifier
        self.listen_host = listen_host
        self.listen_port = int(listen_port)
        self.peers = peers

        # MARK: Setup the communication module
        event_loop = asyncio.get_event_loop()
        self.communicator = HTTPCommunicator(self.identifier,
                                             listen_host=self.listen_host,
                                             listen_port=self.listen_port)
        self.communicator.set_on_heartbeat(self.on_beat)
        event_loop.create_task(self.communicator.start())
        event_loop.create_task(self.pinger())

    async def pinger(self):
        while True:
            for peer in self.peers:
                host = peer['host']
                port = peer['port']
                st = await self.communicator.send_heartbeat(host, port)
                if not st:
                    print("Heartbeat rejected by peer")
            await asyncio.sleep(2)

    def on_beat(self, peer_identifier):
        print(peer_identifier)
        return True

    def is_leader(self):
        return False
