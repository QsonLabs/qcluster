from enum import Enum
import asyncio
import random
import logging
import time

logger = logging.getLogger(__name__)


class PeerState(Enum):
    LEADER = 1
    CANDIDATE = 2
    FOLLOWER = 3
    TERMINATING = 4


class RaftConsensus:
    def __init__(self,
                 communicator,
                 registry,
                 min_timeout=0.150,
                 max_timeout=0.300):
        """
        Creates a RAFT algorithm module to handle leader election
        and consensus.
        """
        self.term = 0
        self.registry = registry
        self.communicator = communicator
        self.communicator.set_on_heartbeat(self.on_heartbeat)
        self.communicator.set_on_request_vote(self.on_request_vote)

        self.state = PeerState.FOLLOWER
        self.known_leader = None
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
                self.known_leader = None
        elif self.state == PeerState.CANDIDATE:
            logger.debug("I am starting an election for term {}"
                         .format(self.term))
            timeout = self.get_timeout()
            t_start = time.time()
            self.got_heartbeat.clear()
            # Send a request vote to all peers
            requests = []
            for peer in self.registry.peers:
                host = peer.host
                port = peer.port
                data = {
                    'identifier': self.communicator.identifier,
                    'term': self.term
                }
                call = self.communicator.request_vote(host, port, data)
                requests.append(asyncio.wait_for(call, timeout=timeout))
            self.has_voted_in_term = True
            results = await asyncio.gather(*requests, return_exceptions=True)
            if not self.got_heartbeat.is_set() and self.is_candidate():
                # Loop through our results and tally votes
                votes = 1
                for ballot in results:
                    if self.parse_ballot(ballot):
                        votes += 1
                outcome = (votes / (self.registry.get_peer_count() + 1))
                majority = outcome > 0.5
                logger.debug("I got {} of the votes on term {}"
                             .format(outcome, self.term))
                if majority:
                    self.state = PeerState.LEADER
                    self.known_leader = self.communicator.identifier
                else:
                    duration = time.time() - t_start
                    await asyncio.sleep(timeout - duration)
                    self.term += 1
        elif self.state == PeerState.LEADER:
            logger.info("I am the leader for term {}".format(self.term))
            t_start = time.time()
            requests = []
            for peer in self.registry.peers:
                host = peer.host
                port = peer.port
                data = {
                    'identifier': self.communicator.identifier,
                    'term': self.term
                }
                call = self.communicator.send_heartbeat(host, port, data)
                requests.append(asyncio.wait_for(call, timeout=0.100))
            await asyncio.gather(*requests, return_exceptions=True)
            duration = time.time() - t_start
            await asyncio.sleep(0.050 - duration)

    def on_heartbeat(self, data):
        """
        We expected the data to have:
            - identifier
            - leader's term
        """
        leader_identifier = data.get('identifier', None)
        leader_term = data.get('term', -1)
        valid_beat = False

        if self.state == PeerState.CANDIDATE and leader_term >= self.term:
            valid_beat = True
        elif self.state == PeerState.LEADER and self.term < leader_term:
            valid_beat = True
        elif self.state == PeerState.FOLLOWER and leader_term >= self.term:
            valid_beat = True

        if valid_beat:
            self.state = PeerState.FOLLOWER
            self.known_leader = leader_identifier
            self.term = leader_term
            logger.debug("I got a heartbeat for term {} from {}"
                         .format(self.term, leader_identifier))
            self.got_heartbeat.set()

    def on_request_vote(self, data):
        """
        We expected the data to have:
            - identifier
            - leader's term
        """
        leader_identifier = data.get('identifier', None)
        candidate_term = data.get('term', -1)
        if candidate_term > self.term:
            self.term = candidate_term
            self.state = PeerState.FOLLOWER
            self.has_voted_in_term = True
            logger.debug("I just voted for {} for term {}"
                         .format(leader_identifier, candidate_term))
            return True, {"vote_granted": True}

        if candidate_term < self.term or self.has_voted_in_term:
            logger.debug("I decline to voted for {} for term {}"
                         .format(leader_identifier, candidate_term))
            return True, {"vote_granted": False}
        else:
            self.has_voted_in_term = True
            logger.debug("I just voted for {} for term {}"
                         .format(leader_identifier, candidate_term))
            return True, {"vote_granted": True}

    # MARK: Helper functions

    @staticmethod
    def parse_ballot(ballot):
        """
        Helper function to parse a response from request_vote.

        An example of the data:
            True, {"vote_granted": True}
        """

        # Ensure we got a tuple
        if type(ballot) != tuple:
            logger.error("Unable to parse ballot: {}".format(ballot))
            return False

        # Ensure the tuple has 2 fields
        if len(ballot) != 2:
            logger.error("Only expected 2 fields in the ballot: {}"
                         .format(ballot))
            return False

        # Check the first field is a bool
        part_1, part_2 = ballot[0], ballot[1]
        if type(part_1) != bool:
            logger.error("Expected a bool in position 1: {}".format(ballot))
            return False

        # We only inspect the ballot if the first part is True
        if not part_1:
            return False

        if type(part_2) != dict:
            logger.error("Expected a dict in position 2: {}".format(ballot))
            return False

        # Return the vote_granted field from the data
        return part_2.get('vote_granted', False)

    def is_candidate(self):
        """Helper to determine if we are a candidate"""
        return self.state == PeerState.CANDIDATE

    def is_leader(self):
        """Helper to determine if we are a leader"""
        return self.state == PeerState.LEADER

    def is_follower(self):
        """Helper to determine if we are a follower"""
        return self.state == PeerState.FOLLOWER
