import pytest
import asyncio
import aiohttp.web
from unittest.mock import Mock, patch
from qcluster.communication import HTTPCommunicator, _HTTPResponder


class TestHTTPCommunicator:

    @pytest.mark.asyncio
    async def test_creates_requestor(self):
        """Test that a requester is initialized"""
        # Setup
        self.communicator = HTTPCommunicator('a', 7000)

        # Assert
        assert self.communicator._requester is not None

    @pytest.mark.asyncio
    async def test_creates_responder(self):
        """Test that a responder is initialized"""
        # Setup
        self.communicator = HTTPCommunicator('a', 7000)

        # Assert
        assert self.communicator._responder is not None

    @pytest.mark.asyncio
    async def test_ping_returns_true(self, unused_tcp_port):
        """Test that a ping comes back"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()

        # Act
        result = await self.communicator.ping('localhost', unused_tcp_port)

        # Assert
        assert result

    @pytest.mark.asyncio
    async def test_ping_returns_false(self, unused_tcp_port):
        """Test that a ping doesn't come back"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()

        # Act
        result = await self.communicator.ping('localhost', 0)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_ping_timeout(self, unused_tcp_port):
        """Test that a ping will timeout"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()

        # Act
        status = await self.communicator.ping('localhost', unused_tcp_port, timeout=0)

        # Assert
        assert status is False

    @pytest.mark.asyncio
    async def test_heartbeat_returns_true(self):
        """Test that sending a heartbeat returns with response code 200"""
        # Setup
        self.communicator = HTTPCommunicator('a', 7000)
        await self.communicator.start()

        # Act
        status, data = await self.communicator.send_heartbeat('localhost', 7000, {'identifier': 'a'})

        # Assert
        assert status is True
        assert data is None

    @pytest.mark.asyncio
    async def test_heartbeat_returns_false_on_error(self, unused_tcp_port):
        """Test that nothing returns on a connection error"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()

        # Act
        status, data = await self.communicator.send_heartbeat('localhost', 0, {})

        # Assert
        assert status is False
        assert data is None

    @pytest.mark.asyncio
    async def test_on_heartbeat_executes(self, unused_tcp_port):
        """Test that our function is called each time we receive a heartbeat"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_heartbeat = Mock()
        on_heartbeat.return_value = True, {}
        self.communicator.set_on_heartbeat(on_heartbeat)
        data = {
            'identifier': 'a',
            'term': 1
        }

        # Act
        await self.communicator.send_heartbeat('localhost', unused_tcp_port, data)

        # Assert
        on_heartbeat.assert_called_with(data)

    @pytest.mark.asyncio
    async def test_on_heartbeat_can_return_error(self, unused_tcp_port):
        """Test that our function can cause an error to be returned"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_heartbeat = Mock()
        on_heartbeat.return_value = (False, {"status", "error!"})
        self.communicator.set_on_heartbeat(on_heartbeat)

        # Act
        status, data = await self.communicator.send_heartbeat('localhost', unused_tcp_port, {})

        # Assert
        assert status is False
        assert data is None

    @pytest.mark.asyncio
    async def test_on_heartbeat_rejects_invalid_data(self, unused_tcp_port):
        """Test that the data parameter rejects non None or dict data."""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()

        # Assert
        with pytest.raises(ValueError):
            await self.communicator.send_heartbeat('localhost', unused_tcp_port, 5)

    @pytest.mark.asyncio
    async def test_on_heartbeat_transforms_none_data(self, unused_tcp_port):
        """Test that the data parameter is an empty dict when None is supplied"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        cb = Mock()
        self.communicator.set_on_heartbeat(cb)

        # Act
        await self.communicator.send_heartbeat('localhost', unused_tcp_port, None)

        # Assert
        cb.assert_called_with({})

    @pytest.mark.asyncio
    async def test_heartbeats_timeout_after_500_ms(self, unused_tcp_port):
        """Test that a heartbeat can timeout after 500ms with no response"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)

        async def long_callback(identifier):
            await asyncio.sleep(1)

        self.communicator.set_on_heartbeat(long_callback)
        await self.communicator.start()

        # Act
        status, data = await self.communicator.send_heartbeat('localhost', unused_tcp_port, {}, timeout=0.5)

        # Assert
        assert status is False
        assert data is None

    @pytest.mark.asyncio
    async def test_register_returns_true(self, unused_tcp_port):
        """Test that registering returns true."""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()

        # Act
        status = await self.communicator.register_with('localhost', unused_tcp_port)

        # Assert
        assert status is True

    @pytest.mark.asyncio
    async def test_on_register_executes(self, unused_tcp_port):
        """Test that our register callback is called with the right data"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_register = Mock()
        self.communicator.set_on_register(on_register)

        # Act
        await self.communicator.register_with('localhost', unused_tcp_port)

        # Assert
        on_register.assert_called_with('localhost', unused_tcp_port, 'a')

    @pytest.mark.asyncio
    async def test_on_register_can_return_error(self, unused_tcp_port):
        """Test that our register callback can force an error"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_register = Mock()
        on_register.return_value = (False, "Error!")
        self.communicator.set_on_register(on_register)

        # Act
        status = await self.communicator.register_with('localhost', unused_tcp_port)

        # Assert
        assert status is False

    @patch.object(aiohttp.web, 'Response')
    def test_respond_text_success(self, web_response):
        """Test that passing a success result with data returns a 200 result
        with text in the body."""
        # Setup
        cb = (True, "Go Hokies!")

        # Act
        _HTTPResponder.respond(cb)

        # Assert
        web_response.assert_called_with(status=200, text="Go Hokies!")

    @patch.object(aiohttp.web, 'Response')
    def test_respond_text_failure(self, web_response):
        """Test that passing a failure result with data returns a 400 result
        with text in the body."""
        # Setup
        cb = (False, "Go Hoos!")

        # Act
        _HTTPResponder.respond(cb)

        # Assert
        web_response.assert_called_with(status=400, text="Go Hoos!")

    @patch.object(aiohttp.web, 'json_response')
    def test_respond_json_success(self, web_response):
        """Test that passing a success result with object data returns a 200
        result with a json result in the body."""
        # Setup
        cb = (True, {"Let's go!": "Hokies!"})

        # Act
        _HTTPResponder.respond(cb)

        # Assert
        web_response.assert_called_with({"Let's go!": "Hokies!"}, status=200)

    @patch.object(aiohttp.web, 'json_response')
    def test_respond_json_failure(self, web_response):
        """Test that passing a success result with object data returns a 400
        result with a json result in the body."""
        # Setup
        cb = (False, {"Boo": "Hoo"})

        # Act
        _HTTPResponder.respond(cb)

        # Assert
        web_response.assert_called_with({"Boo": "Hoo"}, status=400)

    @pytest.mark.asyncio
    async def test_request_vote_returns_400_with_no_callback(self, unused_tcp_port):
        """Test that request vote returns a 400 status when no callback is defined"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        self.communicator.set_on_request_vote(None)

        # Act
        res = await self.communicator._requester.post('localhost', unused_tcp_port, '/raft/request_vote', {'test': 123})

        # Assert
        assert res.status == 400

    @pytest.mark.asyncio
    async def test_request_vote_passes_data_to_callback(self, unused_tcp_port):
        """Test that request vote passed the data to the defined callback"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_request_vote = Mock()
        self.communicator.set_on_request_vote(on_request_vote)
        data = {'test': True}

        # Act
        await self.communicator.request_vote('localhost', unused_tcp_port, data)

        # Assert
        on_request_vote.assert_called_with(data)

    @pytest.mark.asyncio
    async def test_request_votes_timeout_after_500_ms(self, unused_tcp_port):
        """Test that request vote will timeout after a given timeout"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)

        async def long_callback(data):
            await asyncio.sleep(1)

        self.communicator.set_on_request_vote(long_callback)
        await self.communicator.start()

        # Act
        status, data = await self.communicator.request_vote('localhost', unused_tcp_port, {}, timeout=0.5)

        # Assert
        assert status is False
        assert data is None

    @pytest.mark.asyncio
    async def test_request_vote_returns_on_error(self, unused_tcp_port):
        """Test that request vote will return nothing on error"""
        # Setup
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_request_vote = Mock()
        self.communicator.set_on_request_vote(on_request_vote)
        data = {'test': True}

        # Act
        status, data = await self.communicator.request_vote('localhost', 0, data)

        # Assert
        assert status is False
        assert data is None