import pytest
import asyncio
from unittest.mock import Mock
from qcluster.communication import HTTPCommunicator


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
    async def test_heartbeat_returns_true(self):
        """Test that sending a heartbeat returns with response code 200"""
        self.communicator = HTTPCommunicator('a', 7000)
        await self.communicator.start()
        status = self.communicator.send_heartbeat('localhost', 7000)
        assert await status is True

    @pytest.mark.asyncio
    async def test_heartbeat_returns_none_on_error(self, unused_tcp_port):
        """Test that nothing returns on a connection error"""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        status = self.communicator.send_heartbeat('localhost', 0)
        assert await status is None

    @pytest.mark.asyncio
    async def test_on_heartbeat_executes(self, unused_tcp_port):
        """Test that our function is called each time we receive a heartbeat"""
        self.communicator = HTTPCommunicator('a', unused_tcp_port)
        await self.communicator.start()
        on_heartbeat = Mock()
        self.communicator.set_on_heartbeat(on_heartbeat)
        await self.communicator.send_heartbeat('localhost', unused_tcp_port)
        assert on_heartbeat.called_with('b')

    @pytest.mark.asyncio
    async def test_heartbeats_timeout_after_500_ms(self, unused_tcp_port):
        self.communicator = HTTPCommunicator('a', unused_tcp_port)

        async def long_callback(identifier):
            await asyncio.sleep(1)

        self.communicator.set_on_heartbeat(long_callback)
        await self.communicator.start()
        with pytest.raises(asyncio.TimeoutError):
            await self.communicator.send_heartbeat('localhost',
                                                   unused_tcp_port,
                                                   timeout=0.5)

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
