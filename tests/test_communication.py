import pytest
import asyncio
import aiohttp.web
from unittest.mock import Mock, patch
from qcluster.communication import HTTPCommunicator, _HTTPResponder


class TestHTTPCommunicator:

    @pytest.mark.asyncio
    async def test_creates_requestor(self):
        """Test that a requester is initialized"""
        self.communicator = HTTPCommunicator('a', 7000)
        assert self.communicator._requester is not None

    @pytest.mark.asyncio
    async def test_creates_responder(self):
        """Test that a responder is initialized"""
        self.communicator = HTTPCommunicator('a', 7000)
        assert self.communicator._responder is not None

    @pytest.mark.asyncio
    async def test_ping_returns_true(self, unused_tcp_port):
        """Test that a ping comes back"""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        assert await self.communicator.ping('localhost', unused_tcp_port)

    @pytest.mark.asyncio
    async def test_ping_returns_false(self, unused_tcp_port):
        """Test that a ping doesn't come back"""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        assert await self.communicator.ping('localhost', 0) is False

    @pytest.mark.asyncio
    async def test_ping_timeout(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        status = await self.communicator.ping('localhost',
                                              unused_tcp_port,
                                              timeout=0)
        assert status is False

    @pytest.mark.asyncio
    async def test_heartbeat_returns_true(self):
        """Test that sending a heartbeat returns with response code 200"""
        self.communicator = HTTPCommunicator('a', 7000)
        await self.communicator.start()
        status = self.communicator.send_heartbeat('localhost', 7000, 1)
        assert await status is True

    @pytest.mark.asyncio
    async def test_heartbeat_returns_false_on_error(self, unused_tcp_port):
        """Test that nothing returns on a connection error"""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        status = self.communicator.send_heartbeat('localhost', 0, 1)
        assert await status is False

    @pytest.mark.asyncio
    async def test_on_heartbeat_executes(self, unused_tcp_port):
        """Test that our function is called each time we receive a heartbeat"""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_heartbeat = Mock()
        self.communicator.set_on_heartbeat(on_heartbeat)
        await self.communicator.send_heartbeat('localhost', unused_tcp_port, 1)
        assert on_heartbeat.called_with('b')

    @pytest.mark.asyncio
    async def test_on_heartbeat_can_return_error(self, unused_tcp_port):
        """Test that our function can cause an error to be returned"""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_heartbeat = Mock()
        on_heartbeat.return_value = (False, "Error!")
        self.communicator.set_on_heartbeat(on_heartbeat)
        status = await self.communicator.send_heartbeat('localhost', unused_tcp_port, 1)
        assert status is False

    @pytest.mark.asyncio
    async def test_heartbeats_timeout_after_500_ms(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)

        async def long_callback(identifier):
            await asyncio.sleep(1)

        self.communicator.set_on_heartbeat(long_callback)
        await self.communicator.start()
        status = await self.communicator.send_heartbeat('localhost',
                                                        unused_tcp_port,
                                                        1,
                                                        timeout=0.5)
        assert status is False

    @pytest.mark.asyncio
    async def test_register_returns_true(self, unused_tcp_port):
        """Test that registering returns true."""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        status = self.communicator.register_with('localhost', unused_tcp_port)
        assert await status is True

    @pytest.mark.asyncio
    async def test_on_register_executes(self, unused_tcp_port):
        """Test that our register callback is called with the right data"""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_register = Mock()
        self.communicator.set_on_register(on_register)
        await self.communicator.register_with('localhost', unused_tcp_port)
        on_register.assert_called_with('localhost', unused_tcp_port, 'a')

    @pytest.mark.asyncio
    async def test_on_register_can_return_error(self, unused_tcp_port):
        """Test that our register callback can force an error"""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_register = Mock()
        on_register.return_value = (False, "Error!")
        self.communicator.set_on_register(on_register)
        status = await self.communicator.register_with('localhost', unused_tcp_port)
        assert status is False

    @patch.object(aiohttp.web, 'Response')
    def test_respond_text_success(self, web_response):
        """Test that passing a success result with data returns a 200 result
        with text in the body."""
        cb = (True, "Go Hokies!")
        _HTTPResponder.respond(cb)
        web_response.assert_called_with(status=200, text="Go Hokies!")

    @patch.object(aiohttp.web, 'Response')
    def test_respond_text_failure(self, web_response):
        """Test that passing a failure result with data returns a 400 result
        with text in the body."""
        cb = (False, "Go Hoos!")
        _HTTPResponder.respond(cb)
        web_response.assert_called_with(status=400, text="Go Hoos!")

    @patch.object(aiohttp.web, 'json_response')
    def test_respond_json_success(self, web_response):
        """Test that passing a success result with object data returns a 200
        result with a json result in the body."""
        cb = (True, {"Let's go!": "Hokies!"})
        _HTTPResponder.respond(cb)
        web_response.assert_called_with({"Let's go!": "Hokies!"}, status=200)

    @patch.object(aiohttp.web, 'json_response')
    def test_respond_json_failure(self, web_response):
        """Test that passing a success result with object data returns a 400
        result with a json result in the body."""
        cb = (False, {"Boo": "Hoo"})
        _HTTPResponder.respond(cb)
        web_response.assert_called_with({"Boo": "Hoo"}, status=400)
