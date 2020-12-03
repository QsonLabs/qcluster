import logging

logger = logging.getLogger(__name__)


class Peer(object):
    def __init__(self, host, port, identifier, metadata):
        """
        Creates a peer object with a host, port identifier, and some
        metadata.

        Args:
            host: The host to connect to for internal communication
            port: The port to connect to for internal communication
            identifier: A unique identifier for this peer
            metadata: A dictionary of custom peer data
        """
        self.host = host
        self.port = port
        self.identifier = identifier
        self.metadata = metadata

    def is_valid(self):
        if self.host is None:
            return False
        elif self.port == 0:
            return False
        elif self.identifier == "":
            return False
        elif type(self.metadata) is not dict:
            return False
        else:
            return True


class Registry(object):
    def __init__(self, peers_data):
        self.peers = []
        for peer_data in peers_data:
            peer_host = peer_data.get('host', None)
            peer_port = int(peer_data.get('port', 0))
            peer_identifier = peer_data.get('identifier', "")
            peer_metadata = peer_data.get('metadata', {})
            peer = Peer(peer_host, peer_port, peer_identifier, peer_metadata)

            # Validate properties
            if not peer.is_valid():
                logger.error("Invalid peer data: {}".format(peer_data))
                continue
            if self.get_peer_by_identifier(peer_identifier) is not None:
                logger.error("Duplicate identifier: {}"
                             .format(peer_identifier))
                continue
            self.peers.append(peer)

    def get_peer_count(self):
        return len(self.peers)

    def get_peer_by_identifier(self, identifier):
        for peer in self.peers:
            if peer.identifier == identifier:
                return peer
        return None
