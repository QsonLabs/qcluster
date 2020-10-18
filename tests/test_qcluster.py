import pytest

from qcluster import QCluster


class TestQCluster:

    @pytest.mark.asyncio
    async def test_qcluster(self, unused_tcp_port):
        cluster = QCluster('test_identifier', unused_tcp_port)
        assert cluster.is_leader() is False
