from qcluster import QCluster
import asyncio
import logging
import sys
import json


async def main():
    logger = logging.getLogger()
    logger.name = "service"
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(name)-30s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)

    conf_file = sys.argv[1]
    with open(conf_file) as f:
        conf = json.load(f)

    identifier = conf['identifier']
    # host = conf['listen_host']
    # port = conf['listen_port']
    # peers = conf['peers']

    # cluster = QCluster(identifier, port, peers=peers)
    cluster = QCluster(**conf)
    while True:
        if cluster.is_leader():
            logger.info("I am the leader!")
            logger.info("{} is doing some work...".format(identifier))
        else:
            logger.info("I am not the leader :(")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
