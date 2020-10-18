from enum import Enum
import asyncio
import random


class PeerState(Enum):
    LEADER = 1
    CANDIDATE = 2
    FOLLOWER = 3
    TERMINATING = 4


class RaftConsensus:
    def __init__(self,
                 communicator,
                 peers=[],
                 min_timeout=0.150,
                 max_timeout=0.300):
        """
        Creates a RAFT algorithm module to handle leader election
        and consensus.
        """
        self.term = 0
        self.peers = peers
        self.communicator = communicator
        self.communicator.set_on_heartbeat(self.on_heartbeat)
        self.communicator.set_on_request_vote(self.on_request_vote)

        self.state = PeerState.FOLLOWER
        self.min_timeout = min_timeout
        self.max_timeout = max_timeout
        self.has_voted_in_term = False

        self.got_heartbeat = asyncio.Event()

    def get_timeout(self):
        """Generates a timeout interval between our min and max."""
        return random.uniform(self.min_timeout, self.max_timeout)

    async def start(self):
        while self.state != PeerState.TERMINATING:
            await self.process_state()

    async def process_state(self):
        if self.state == PeerState.FOLLOWER:
            try:
                await asyncio.wait_for(self.got_heartbeat.wait(),
                                       self.get_timeout())
                self.got_heartbeat.clear()
            except asyncio.exceptions.TimeoutError:
                self.state = PeerState.CANDIDATE
                self.term += 1
        elif self.state == PeerState.CANDIDATE:
            # self.has_voted_in_term = True
            self.got_heartbeat.clear()
            # Send a request vote to all peers
            requests = []
            for peer in self.peers:
                host = peer.get('host')
                port = peer.get('port')
                data = {
                    'identifier': self.communicator.identifier,
                    'term': self.term
                }
                call = self.communicator.request_vote(host, port, data)
                requests.append(asyncio.wait_for(call, timeout=self.get_timeout()))
            self.has_voted_in_term = True
            results = await asyncio.gather(*requests, return_exceptions=True)
            if not self.got_heartbeat.is_set():
                # Loop through our results and tally votes
                votes = 1
                for ballot in results:
                    valid = type(ballot) == tuple and ballot[0] and type(ballot[1]) is dict
                    if valid and ballot[1].get('vote_granted', False):
                        votes += 1
                outcome = (votes / (len(self.peers) + 1))
                majority = outcome > 0.5
                print("I got {} of the votes".format(outcome))
                if majority:
                    self.state = PeerState.LEADER
        elif self.state == PeerState.LEADER:
            # Periodically send a heartbeat to all known peers
            await asyncio.sleep(0.050)
            requests = []
            for peer in self.peers:
                host = peer.get('host')
                port = peer.get('port')
                data = {
                    'identifier': self.communicator.identifier,
                    'term': self.term
                }
                call = self.communicator.send_heartbeat(host, port, data)
                requests.append(asyncio.wait_for(call, timeout=0.100))
            await asyncio.gather(*requests, return_exceptions=True)

    def on_heartbeat(self, data):
        """
        We expected the data to have:
            - identifier
            - leader's term
        """
        # leader_identifier = data.get('identifier', None)
        leader_term = data.get('term', -1)

        if self.state == PeerState.CANDIDATE and leader_term >= self.term:
            self.state = PeerState.FOLLOWER
            self.got_heartbeat.set()
        elif self.state == PeerState.LEADER and self.term < leader_term:
            self.state = PeerState.FOLLOWER
            self.got_heartbeat.set()
        elif self.state == PeerState.FOLLOWER and leader_term >= self.term:
            self.term = leader_term
            self.got_heartbeat.set()

        """
        if self.term < leader_term:
            if self.state in (PeerState.LEADER, PeerState.CANDIDATE):
                self.state = PeerState.FOLLOWER
            else:
                self.term = leader_term
        """
        # self.got_heartbeat.set()

    def on_request_vote(self, data):
        """
        We expected the data to have:
            - identifier
            - leader's term
        """
        # leader_identifier = data.get('identifier', None)
        candidate_term = data.get('term', -1)
        if candidate_term < self.term or self.has_voted_in_term:
            return True, {"vote_granted": False}
        else:
            self.has_voted_in_term = True
            return True, {"vote_granted": True}

        """
        if not self.has_voted_in_term:
            # We will vote for this candidate
            self.has_voted_in_term = True
            return True, {"vote_granted": True}
        else:
            # Already voted
            return True, {"vote_granted": False}
        """
