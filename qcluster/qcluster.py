import asyncio
import logging
from qcluster.communication import HTTPCommunicator

logger = logging.getLogger(__name__)


class QCluster(object):
    def __init__(self,
                 identifier='',
                 listen_host='localhost',
                 listen_port=0,
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
            heartbeats = []
            for peer in self.peers:
                host = peer['host']
                port = peer['port']
                # st = await self.communicator.send_heartbeat(host, port)
                # if not st:
                #     self.logger.info("Heartbeat rejected by peer")
                heartbeats.append(self.communicator.send_heartbeat(host, port))
            results = await asyncio.gather(*heartbeats)
            print(results)
            await asyncio.sleep(0.3)

    def on_beat(self, peer_identifier):
        logger.info("Got heartbeat from {}".format(peer_identifier))
        return True

    def is_leader(self):
        return False
