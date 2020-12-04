# QCluster
Quick Cluster - a simple service registry for fail-over and replication.

## Context and Problem
In modern services it is expected that fail-over, replication or both are provided out of the box. Especially in a distributed cloud architecture, where nodes can be spun up on demand, registering new services is an essential part of ensuring both scalability and reliability. There are several robust solutions for service management that include Apache Zookeeper, Istio Service Mesh, and Linkerd. Each of these either implement a proxy for traffic or have complex architecture requirements. Sometimes a service does not want the full suite of features and needs a lightweight way to handle fail-over.

## Solution
QCluster is intended to be a lightweight service that enables fail-over and replication for services that do not need the heavy lift associated with other service mesh tools. This can be achieved by:

- Ensuring that QCluster clients can run in a master-less environment
- Allowing for a master-minion model as well, which may benefit stateful applications
- Encouraging self registration 
- Enabling built in metrics
- Api access and client SDKs


## Contributing
The QCluster project was built using tox which exposes some development tools. Running tox automatically runs flake8 to check the code style as well as running the suite of unit tests and generating code coverage reports.

To run the unit tests, simply run tox in the project directory:
```
[Aarons-MacBook-Pro:qcluster] Aaron% tox
...
py38 run-test: commands[1] | coverage report
Name                        Stmts   Miss  Cover
-----------------------------------------------
qcluster/__init__.py            2      0   100%
qcluster/communication.py     147      0   100%
qcluster/consensus.py         134      3    98%
qcluster/qcluster.py           23      3    87%
qcluster/registry.py           41      9    78%
qcluster/utils.py              18      0   100%
-----------------------------------------------
TOTAL                         365     15    96%
py38 run-test: commands[2] | coverage html
py38 run-test: commands[3] | flake8 qcluster
____________________________________________________ summary _____________________________________________________
  py38: commands succeeded
  congratulations :)
```

Please keep the following practices in mind when contributing to the project:

- Conform to the flake8 styling guidelines for consistency
- Strive to add unit tests for new code added

## Python Support

Currently only Python 3.8 is supported, but this may run on later versions of Python. The [asyncio library](https://docs.python.org/3/library/asyncio.html) is heavily relied on which will be the main driving factor in which versions of Python are supported.

## QCluster SDK

### `is_leader()`

Used to determine if the current peer is the leader of the cluster.

```py
cluster = QCluster(**configuration)
if cluster.is_leader():
    print("I am the leader")
else:
    print("I am a follower")
```

### `get_leader_info()`

Used to get more detailed information about the known elected leader. If no leader is elected (in cases where a majority vote is impossible to achieve), this will return `None`.

The leader will be returned in a `Peer` object which has the following properties:

- host:         The host that this peer can be reached at for QCluster communication
- port:         The port that this peer can be reached at for QCluster communication
- identifier:   The unique string identifier of this peer
- metadata:     A dictionary of metadata that has been supplied by the configuration file.

```py
cluster = QCluster(**configuration)
leader = cluster.get_leader_info()

print("Leader communicates with QCluster on {}:{}".format(leader.host, leader.port))
print("Leader has an identifier of: {}".format(leader.identifier))
print("Leader has custom metadata of: {}".format(leader.metadata))
```

```
Leader communicates with QCluster on localhost:7001
Leader has an identifier of: server_a
Leader has custom metadata of: {"custom_field": 5"}
```

## Examples

Some examples of using QCluster are shown below using the following configuration file (adapted for individual peers with the appropriate fields changed).

```JSON
{
    "identifier": "server_a",
    "listen_host": "localhost",
    "listen_port": 7001,
    "peers": [
        {"host": "localhost", "port": 7002, "identifier":  "server_b"},
        {"host": "localhost", "port": 7003, "identifier":  "server_c"}
    ]
}
```

This configuration represents a single peer, `server_a`, that will accept QCluster data on `localhost:7001`. It has 2 peers, `server_b` and `server_c` which can be connected to at `localhost:7002` and `localhost:7003` respectively.

The configuration file for peers `server_b` and `server_c` would be formatted similarly, but with appropriate data for each peer to know about each of the other peers.

### Custom Metadata

A peer can have custom metadata associated with it in the configuration file. Changing a peer entry to:

```JSON
{"host": "localhost", "port": 7002, "identifier":  "server_b", "metadata": {"server_port":  8002}}
```

results in this peer having the data `{"server_port": 8002}` accessible to all other peers in the `metadata` property. Therefore, follower peers can have access to more information about the elected leader to perform more complex tasks as a follower (such as redirecting one's traffic to the leader).

### Bare Minimum
```py
from qcluster import QCluster
import asyncio
import sys
import json


async def main():
    conf_file = sys.argv[1]
    with open(conf_file) as f:
        conf = json.load(f)

    identifier = conf['identifier']
    cluster = QCluster(**conf)
    while True:
        if cluster.is_leader():
            logger.info("I am the leader!")
            logger.info("{} is doing some work...".format(identifier))
        else:
            logger.info("I am not the leader :(")
            logger.info("This is the leader: {}".format(cluster.get_leader_info()))
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

Running this program with the 3 versions of the configuration file for `server_a`, `server_b`, and `server_c` would result in a single peer becoming leader. The work loop of each peer would then either do "work" if it was the leader, or sit idle until it becomes the leader.

### Advanced Examples

Please look in the examples directory for find some more in-depth and specific examples.
