from qcluster import QCluster
import asyncio
import sys
import json


async def main():
    conf_file = sys.argv[1]
    with open(conf_file) as f:
        conf = json.load(f)

    identifier = conf['identifier']
    # host = conf['listen_host']
    port = conf['listen_port']
    peers = conf['peers']

    cluster = QCluster(identifier, port, peers=peers)
    while True:
        if cluster.is_leader():
            print("I am the leader!")
        print("{} is doing some work...".format(identifier))
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
