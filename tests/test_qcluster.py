from qcluster import QCluster


def test_qcluster():
    cluster = QCluster(5)
    assert cluster.get_x() == 5
