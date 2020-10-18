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
        assert result == (True, 5)

    @pytest.mark.asyncio
    async def test_call_sync_callback(self):
        """Test calling a synchronous callback"""
        def long_result():
            time.sleep(0.5)
            return 5

        t1 = time.time()
        result = await utils.call_callback(long_result)
        assert time.time() - t1 > 0.5
        assert result == (True, 5)

    @pytest.mark.asyncio
    async def test_call_callback_uncallable(self):
        """Test calling an uncallable callback."""
        with pytest.raises(ValueError):
            await utils.call_callback(5)

    def test_interpret_callback_result_boolean(self):
        """Test that a callback result is transformed into the right format."""
        r_true = utils.interpret_callback_result(True)
        r_false = utils.interpret_callback_result(False)
        assert r_true == (True, None)
        assert r_false == (False, None)

    def test_interpret_callback_result_dual_tuple(self):
        """Test that a callback result is transformed into the right format."""
        r_true = utils.interpret_callback_result((True, 67))
        r_false = utils.interpret_callback_result((False, {'e': 'fail'}))
        assert r_true == (True, 67)
        assert r_false == (False, {'e': 'fail'})

    def test_interpret_callback_result_dual_tuple_data_first(self):
        """Test that a callback result is transformed into the right format."""
        r_true = utils.interpret_callback_result((128, 67))
        assert r_true == (True, 67)

    def test_interpret_callback_result_3_tuple(self):
        """Test that a callback result is transformed into the right format."""
        r_true = utils.interpret_callback_result((True, 67, 8))
        r_false = utils.interpret_callback_result((False, {'e': 'fail'}, False))
        assert r_true == (True, 67)
        assert r_false == (False, {'e': 'fail'})

    def test_interpret_callback_response_none(self):
        """Test that a callback result is transformed into the right format."""
        r = utils.interpret_callback_result(None)
        assert r == (False, None)

    def test_interpret_callback_response_only_data(self):
        """Test that a callback result is transformed into the right format."""
        r = utils.interpret_callback_result(5)
        assert r == (True, 5)
