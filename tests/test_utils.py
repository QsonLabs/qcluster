import asyncio
import pytest
import time

from qcluster import utils


class TestUtils:

    @pytest.mark.asyncio
    async def test_call_async_callback(self):
        """Test calling an async callback."""
        async def long_result():
            await asyncio.sleep(0.5)
            return 5

        t1 = time.time()
        result = await utils.call_callback(long_result)
        assert time.time() - t1 > 0.5
        assert result == 5

    @pytest.mark.asyncio
    async def test_call_sync_callback(self):
        """Test calling a synchronous callback"""
        def long_result():
            time.sleep(0.5)
            return 5

        t1 = time.time()
        result = await utils.call_callback(long_result)
        assert time.time() - t1 > 0.5
        assert result == 5

    @pytest.mark.asyncio
    async def test_call_callback_uncallable(self):
        """Test calling an uncallable callback."""
        with pytest.raises(ValueError):
            await utils.call_callback(5)
