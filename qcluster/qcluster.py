import asyncio
import logging
from qcluster.communication import HTTPCommunicator
from qcluster.consensus import RaftConsensus, PeerState
from qcluster.registry import Registry

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

        # MARK: Setup the communication module
        event_loop = asyncio.get_event_loop()
        self.communicator = HTTPCommunicator(self.identifier,
                                             listen_host=self.listen_host,
                                             listen_port=self.listen_port)
        self.registry = Registry(peers)
        self.raft = RaftConsensus(self.communicator, self.registry)

        event_loop.create_task(self.communicator.start())
        event_loop.create_task(self.raft.start())

    def is_leader(self):
        return self.raft.state == PeerState.LEADER

    def get_leader_info(self):
        if self.raft.known_leader is not None:
            return self.registry.get_peer_by_identifier(self.raft.known_leader)
        else:
            return None
