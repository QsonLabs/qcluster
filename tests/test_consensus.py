import asyncio
import pytest
import time

from qcluster.consensus import RaftConsensus, PeerState
from qcluster.communication import HTTPCommunicator
from qcluster.registry import Registry

from unittest.mock import Mock, patch


class TestConsensus:

    @pytest.mark.asyncio
    async def test_term_starts_at_0(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)

        assert self.raft.term == 0

    @pytest.mark.asyncio
    async def test_state_starts_as_follower(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)

        assert self.raft.state == PeerState.FOLLOWER

    @pytest.mark.asyncio
    async def test_get_timeout_returns_valid_default_timeout_value(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)

        t = self.raft.get_timeout()
        assert 0.150 <= t <= 0.300

    @pytest.mark.asyncio
    async def test_get_timeout_returns_valid_custom_timeout_value(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry, min_timeout=0.50, max_timeout=0.60)

        t = self.raft.get_timeout()
        assert 0.50 <= t <= 0.60

    @pytest.mark.asyncio
    async def test_no_heartbeat_follower_becomes_candidate(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)
        await self.raft.process_state()

        assert self.raft.term == 1
        assert self.raft.state == PeerState.CANDIDATE

    @pytest.mark.asyncio
    async def test_no_heartbeat_follower_becomes_candidate_high_term(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)
        self.raft.term = 8
        await self.raft.process_state()

        assert self.raft.term == 9
        assert self.raft.state == PeerState.CANDIDATE

    @pytest.mark.asyncio
    async def test_heartbeat_follower_stays_follower(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)
        self.raft.got_heartbeat.set()
        await self.raft.process_state()

        assert self.raft.state == PeerState.FOLLOWER

    @pytest.mark.asyncio
    async def test_valid_heartbeat_sets_got_heartbeat(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)

        data = {
            'identifier': '1',
            'term': self.raft.term
        }

        self.raft.on_heartbeat(data)
        assert self.raft.got_heartbeat.is_set()

    @pytest.mark.asyncio
    async def test_valid_heartbeat_sets_got_heartbeat_and_term_updated(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)

        data = {
            'identifier': '1',
            'term': self.raft.term + 1
        }

        self.raft.on_heartbeat(data)

        assert self.raft.got_heartbeat.is_set()
        assert self.raft.term == data.get('term')

    @pytest.mark.asyncio
    async def test_valid_heartbeat_newer_term_demotes_leader_to_follower(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)
        self.raft.state = PeerState.LEADER

        data = {
            'identifier': '1',
            'term': self.raft.term + 1
        }

        self.raft.on_heartbeat(data)

        assert self.raft.state == PeerState.FOLLOWER

    @pytest.mark.asyncio
    async def test_valid_heartbeat_newer_term_demotes_candidate_to_follower(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)
        self.raft.state = PeerState.CANDIDATE

        data = {
            'identifier': '1',
            'term': self.raft.term + 1
        }

        self.raft.on_heartbeat(data)

        assert self.raft.state == PeerState.FOLLOWER

    @pytest.mark.asyncio
    async def test_process_state_resets_heatbeat_flag(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.registry = Registry([])
        self.raft = RaftConsensus(self.communicator, self.registry)

        data = {
            'identifier': '1',
            'term': self.raft.term
        }

        self.raft.on_heartbeat(data)
        assert self.raft.got_heartbeat.is_set()
        await self.raft.process_state()
        assert self.raft.got_heartbeat.is_set() is False

    @pytest.mark.asyncio
    async def test_leader_sets_followers_heartbeat_flag(self, unused_tcp_port_factory):
        port_l, port_f = unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_l = HTTPCommunicator('leader', port_l)
        self.communicator_f = HTTPCommunicator('follower', port_f)
        await self.communicator_f.start()
        self.raft_l = RaftConsensus(self.communicator_l, Registry([{'host': 'localhost', 'port': port_f, 'identifier': 'follower'}]))
        self.raft_f = RaftConsensus(self.communicator_f, Registry([{'host': 'localhost', 'port': port_l, 'identifier': 'leader'}]))

        self.raft_l.state = PeerState.LEADER

        assert self.raft_f.got_heartbeat.is_set() is False
        await self.raft_l.process_state()
        assert self.raft_f.got_heartbeat.is_set()
        await self.raft_f.process_state()
        assert self.raft_f.got_heartbeat.is_set() is False

    @pytest.mark.asyncio
    async def test_leader_gives_up_on_followers_long_heartbeat(self, unused_tcp_port_factory):
        port_l, port_f = unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_l = HTTPCommunicator('leader', port_l)
        self.communicator_f = HTTPCommunicator('follower', port_f)
        await self.communicator_f.start()
        self.raft_l = RaftConsensus(self.communicator_l, Registry([{'host': 'localhost', 'port': port_f, 'identifier': 'follower'}]))
        self.raft_f = RaftConsensus(self.communicator_f, Registry([{'host': 'localhost', 'port': port_l, 'identifier': 'leader'}]))
        self.raft_l.state = PeerState.LEADER

        async def long_call(data):
            await asyncio.sleep(0.5)

        self.communicator_f.set_on_heartbeat(long_call)

        t_start = time.time()
        await self.raft_l.process_state()
        duration = time.time() - t_start - 0.050

        assert duration <= 0.15

    @pytest.mark.asyncio
    async def test_candidate_sends_votes(self, unused_tcp_port_factory):
        port_c, port_f = unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_c = HTTPCommunicator('candidate', port_c)
        self.communicator_f = HTTPCommunicator('follower', port_f)
        await self.communicator_f.start()
        self.raft_c = RaftConsensus(self.communicator_c, Registry([{'host': 'localhost', 'port': port_f, 'identifier': 'follower'}]))
        self.raft_f = RaftConsensus(self.communicator_f, Registry([{'host': 'localhost', 'port': port_c, 'identifier': 'candidate'}]))

        self.raft_c.state = PeerState.CANDIDATE
        self.raft_c.term = 4

        on_rv = Mock()
        on_rv.return_value = True, {"vote_granted": True}
        self.communicator_f.set_on_request_vote(on_rv)

        await self.raft_c.process_state()

        on_rv.assert_called_with({'identifier': 'candidate', 'term': 4})

    @pytest.mark.asyncio
    async def test_valid_heartbeat_cancels_election(self, unused_tcp_port_factory):
        port_c, port_l = unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_c = HTTPCommunicator('candidate', port_c)
        self.communicator_l = HTTPCommunicator('leader', port_l)
        await self.communicator_l.start()
        self.raft_c = RaftConsensus(self.communicator_c, Registry([{'host': 'localhost', 'port': port_l, 'identifier': 'leader'}]))
        self.raft_l = RaftConsensus(self.communicator_l, Registry([{'host': 'localhost', 'port': port_c, 'identifier': 'candidate'}]))

        self.raft_c.state = PeerState.CANDIDATE
        self.raft_c.term = 4
        self.raft_l.term = 4

        async def rv(data):
            self.raft_c.on_heartbeat({'identifier': 'leader', 'term': self.raft_l.term})

        self.communicator_l.set_on_request_vote(rv)
        await self.raft_c.process_state()

        assert self.raft_c.state == PeerState.FOLLOWER

    @pytest.mark.asyncio
    async def test_invalid_heartbeat_does_not_cancel_election(self, unused_tcp_port_factory):
        port_c, port_l = unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_c = HTTPCommunicator('candidate', port_c)
        self.communicator_l = HTTPCommunicator('leader', port_l)
        await self.communicator_l.start()
        self.raft_c = RaftConsensus(self.communicator_c, Registry([{'host': 'localhost', 'port': port_l, 'identifier': 'leader'}]))
        self.raft_l = RaftConsensus(self.communicator_l, Registry([{'host': 'localhost', 'port': port_c, 'identifier': 'candidate'}]))

        self.raft_c.state = PeerState.CANDIDATE
        self.raft_c.term = 4
        self.raft_l.term = 4

        async def rv(data):
            self.raft_c.on_heartbeat({'identifier': 'leader', 'term': self.raft_c.term - 1})

        self.communicator_l.set_on_request_vote(rv)
        await self.raft_c.process_state()

        assert self.raft_c.state != PeerState.FOLLOWER

    @pytest.mark.asyncio
    async def test_candidate_becomes_leader_after_majority_votes(self, unused_tcp_port_factory):
        port_a, port_b, port_c, port_d = unused_tcp_port_factory(), unused_tcp_port_factory(), unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_a = HTTPCommunicator('a', port_a)
        self.communicator_b = HTTPCommunicator('b', port_b)
        self.communicator_c = HTTPCommunicator('c', port_c)
        self.communicator_d = HTTPCommunicator('d', port_d)
        self.raft_a = RaftConsensus(self.communicator_a, Registry([
            {'host': 'localhost', 'port': port_b, 'identifier': 'b'},
            {'host': 'localhost', 'port': port_c, 'identifier': 'c'},
            {'host': 'localhost', 'port': port_d, 'identifier': 'd'},
        ]))
        self.raft_b = RaftConsensus(self.communicator_b, Registry([
            {'host': 'localhost', 'port': port_a, 'identifier': 'a'},
            {'host': 'localhost', 'port': port_c, 'identifier': 'c'},
            {'host': 'localhost', 'port': port_d, 'identifier': 'd'},
        ]))
        self.raft_c = RaftConsensus(self.communicator_c, Registry([
            {'host': 'localhost', 'port': port_a, 'identifier': 'a'},
            {'host': 'localhost', 'port': port_b, 'identifier': 'b'},
            {'host': 'localhost', 'port': port_d, 'identifier': 'd'},
        ]))
        self.raft_d = RaftConsensus(self.communicator_d, Registry([
            {'host': 'localhost', 'port': port_a, 'identifier': 'a'},
            {'host': 'localhost', 'port': port_b, 'identifier': 'b'},
            {'host': 'localhost', 'port': port_c, 'identifier': 'c'},
        ]))
        await self.communicator_a.start()
        await self.communicator_b.start()
        await self.communicator_c.start()
        await self.communicator_d.start()

        self.raft_a.state = PeerState.CANDIDATE

        def on_rv(data):
            return True, {"vote_granted": True}

        self.communicator_b.set_on_request_vote(on_rv)
        self.communicator_c.set_on_request_vote(on_rv)
        self.communicator_d.set_on_request_vote(on_rv)

        await self.raft_a.process_state()
        assert self.raft_a.state == PeerState.LEADER


    @pytest.mark.asyncio
    async def test_candidate_retries_election_on_split_votes(self, unused_tcp_port_factory):
        port_a, port_b, port_c, port_d = unused_tcp_port_factory(), unused_tcp_port_factory(), unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_a = HTTPCommunicator('a', port_a)
        self.communicator_b = HTTPCommunicator('b', port_b)
        self.communicator_c = HTTPCommunicator('c', port_c)
        self.communicator_d = HTTPCommunicator('d', port_d)
        self.raft_a = RaftConsensus(self.communicator_a, Registry([
            {'host': 'localhost', 'port': port_b, 'identifier': 'b'},
            {'host': 'localhost', 'port': port_c, 'identifier': 'c'},
            {'host': 'localhost', 'port': port_d, 'identifier': 'd'},
        ]))
        self.raft_b = RaftConsensus(self.communicator_b, Registry([
            {'host': 'localhost', 'port': port_a, 'identifier': 'a'},
            {'host': 'localhost', 'port': port_c, 'identifier': 'c'},
            {'host': 'localhost', 'port': port_d, 'identifier': 'd'},
        ]))
        self.raft_c = RaftConsensus(self.communicator_c, Registry([
            {'host': 'localhost', 'port': port_a, 'identifier': 'a'},
            {'host': 'localhost', 'port': port_b, 'identifier': 'b'},
            {'host': 'localhost', 'port': port_d, 'identifier': 'd'},
        ]))
        self.raft_d = RaftConsensus(self.communicator_d, Registry([
            {'host': 'localhost', 'port': port_a, 'identifier': 'a'},
            {'host': 'localhost', 'port': port_b, 'identifier': 'b'},
            {'host': 'localhost', 'port': port_c, 'identifier': 'c'},
        ]))
        await self.communicator_a.start()
        await self.communicator_b.start()
        await self.communicator_c.start()
        await self.communicator_d.start()

        self.raft_a.state = PeerState.CANDIDATE

        def on_rv_true(data):
            return True, {"vote_granted": True}

        def on_rv_false(data):
            return True, {"vote_granted": False}

        self.communicator_b.set_on_request_vote(on_rv_true)
        self.communicator_c.set_on_request_vote(on_rv_false)
        self.communicator_d.set_on_request_vote(on_rv_false)

        await self.raft_a.process_state()
        assert self.raft_a.state == PeerState.CANDIDATE

    @pytest.mark.asyncio
    async def test_old_candidate_rejected_by_newer_term(self, unused_tcp_port_factory):
        port_c, port_f = unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_c = HTTPCommunicator('candidate', port_c)
        self.communicator_f = HTTPCommunicator('leader', port_f)
        await self.communicator_f.start()
        self.raft_c = RaftConsensus(self.communicator_c, Registry([{'host': 'localhost', 'port': port_f, 'identifier': 'follower'}]))
        self.raft_f = RaftConsensus(self.communicator_f, Registry([{'host': 'localhost', 'port': port_c, 'identifier': 'candidate'}]))

        self.raft_c.state = PeerState.CANDIDATE
        self.raft_c.term = 3
        self.raft_f.term = 4

        await self.raft_c.process_state()

        assert self.raft_c.state == PeerState.CANDIDATE

    @pytest.mark.asyncio
    async def test_candidate_only_votes_once(self, unused_tcp_port_factory):
        port_1, port_2 = unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_1 = HTTPCommunicator('candidate_1', port_1)
        self.communicator_2 = HTTPCommunicator('candidate_2', port_2)
        await self.communicator_1.start()
        await self.communicator_2.start()
        self.raft_1 = RaftConsensus(self.communicator_1, Registry([{'host': 'localhost', 'port': port_1, 'identifier': 'candidate_1'}]))
        self.raft_2 = RaftConsensus(self.communicator_2, Registry([{'host': 'localhost', 'port': port_2, 'identifier': 'candidate_2'}]))

        self.raft_1.state = PeerState.CANDIDATE
        self.raft_2.state = PeerState.CANDIDATE

        async def rv():
            return True, {"vote_granted": True}
        self.communicator_2.set_on_request_vote(rv)

        await self.raft_1.process_state()
        await self.raft_2.process_state()

        assert self.raft_1.state == PeerState.CANDIDATE
        assert self.raft_2.state == PeerState.CANDIDATE

    @pytest.mark.asyncio
    async def test_follower_will_vote_for_newer_term(self, unused_tcp_port_factory):
        port_1, port_2, port_3 = unused_tcp_port_factory(), unused_tcp_port_factory(), unused_tcp_port_factory()
        self.communicator_1 = HTTPCommunicator('candidate_1', port_1)
        self.communicator_2 = HTTPCommunicator('candidate_2', port_2)
        self.communicator_3 = HTTPCommunicator('candidate_3', port_3)
        await self.communicator_1.start()
        await self.communicator_2.start()
        await self.communicator_3.start()
        self.raft_1 = RaftConsensus(self.communicator_1, Registry([{'host': 'localhost', 'port': port_1, 'identifier': 'candidate_1'}]))
        self.raft_2 = RaftConsensus(self.communicator_2, Registry([{'host': 'localhost', 'port': port_2, 'identifier': 'candidate_2'}]))
        self.raft_3 = RaftConsensus(self.communicator_3, Registry([{'host': 'localhost', 'port': port_3, 'identifier': 'candidate_3'}]))

        self.raft_1.term = 87
        self.raft_1.state = PeerState.CANDIDATE
        self.raft_1.has_voted_in_term = True

        self.raft_2.term = 87
        self.raft_2.state = PeerState.CANDIDATE
        self.raft_2.has_voted_in_term = True

        self.raft_3.term = 86
        self.raft_3.state = PeerState.FOLLOWER

        # Simulate raft_1 sending a request vote
        data_1 = {"identifier": "candidate_1", "term": self.raft_1.term}
        assert self.raft_2.on_request_vote(data_1) == (True, {"vote_granted": False})
        assert self.raft_3.on_request_vote(data_1) == (True, {"vote_granted": True})
        assert self.raft_3.term == 87
        assert self.raft_3.state == PeerState.FOLLOWER
        assert self.raft_3.has_voted_in_term

    @pytest.mark.asyncio
    async def test_parse_ballot_returns_false_with_non_tuple(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        ballot = None
        assert self.raft.parse_ballot(ballot) is False

    @pytest.mark.asyncio
    async def test_parse_ballot_returns_false_with_incorrect_tuple_fields(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        ballot = None, False, 5
        assert self.raft.parse_ballot(ballot) is False

    @pytest.mark.asyncio
    async def test_parse_ballot_returns_false_with_incorrect_first_field(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        ballot = None, {}
        assert self.raft.parse_ballot(ballot) is False

    @pytest.mark.asyncio
    async def test_parse_ballot_returns_false_with_false_first_field(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        ballot = False, {}
        assert self.raft.parse_ballot(ballot) is False

    @pytest.mark.asyncio
    async def test_parse_ballot_returns_false_with_incorrect_second_field(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        ballot = True, 4
        assert self.raft.parse_ballot(ballot) is False

    @pytest.mark.asyncio
    async def test_parse_ballot_returns_true_with_ballot_vote(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        ballot = True, {'vote_granted': True}
        assert self.raft.parse_ballot(ballot)

    @pytest.mark.asyncio
    async def test_parse_ballot_returns_false_with_ballot_no_vote(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        ballot = None, {'vote_granted': False}
        assert self.raft.parse_ballot(ballot) is False

    @pytest.mark.asyncio
    async def test_parse_ballot_returns_false_with_missing_ballot_data(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        ballot = None, {'garbage': True}
        assert self.raft.parse_ballot(ballot) is False

    @pytest.mark.asyncio
    async def test_is_leader_returns_true_when_leader(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        self.raft.state = PeerState.LEADER
        assert self.raft.is_leader()

    @pytest.mark.asyncio
    async def test_is_leader_returns_false_when_not_leader(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        self.raft.state = PeerState.FOLLOWER
        assert self.raft.is_leader() is False
        self.raft.state = PeerState.CANDIDATE
        assert self.raft.is_leader() is False

    @pytest.mark.asyncio
    async def test_is_follower_returns_true_when_follower(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        self.raft.state = PeerState.FOLLOWER
        assert self.raft.is_follower()

    @pytest.mark.asyncio
    async def test_is_follower_returns_false_when_not_folower(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        self.raft.state = PeerState.LEADER
        assert self.raft.is_follower() is False
        self.raft.state = PeerState.CANDIDATE
        assert self.raft.is_follower() is False

    @pytest.mark.asyncio
    async def test_is_candidate_returns_true_when_candidate(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        self.raft.state = PeerState.CANDIDATE
        assert self.raft.is_candidate()

    @pytest.mark.asyncio
    async def test_is_candidate_returns_false_when_not_candidate(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        self.raft = RaftConsensus(self.communicator, Registry([]))
        self.raft.state = PeerState.FOLLOWER
        assert self.raft.is_candidate() is False
        self.raft.state = PeerState.LEADER
        assert self.raft.is_candidate() is False
