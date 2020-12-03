from qcluster import QCluster
import logging
import sys
import json
import asyncio
from aiohttp import web


def main():
    logger = logging.getLogger()
    logger.name = "server"
    log_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(name)-30s %(levelname)-8s %(message)s')
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    logging.getLogger('qcluster.communication').setLevel(logging.WARNING)
    logging.getLogger('qcluster.communication.aiohttp').setLevel(logging.WARNING)
    logging.getLogger('qcluster.consensus').setLevel(logging.WARNING)

    conf_file = sys.argv[1]
    with open(conf_file) as f:
        conf = json.load(f)

    identifier = conf['identifier']
    server_port = conf['server_port']
    cluster = QCluster(identifier=identifier, listen_host=conf['listen_host'], listen_port=conf['listen_port'], peers=conf['peers'])

    @web.middleware
    async def redirect_to_leader(request, handler):
        if not cluster.is_leader():
            # We should redirect to the leader
            leader = cluster.get_leader_info()
            leader_host = leader.host
            leader_port = leader.metadata.get('server_port')
            path = request.path
            logger.info("Redirecting to the leader: {}:{}{}".format(leader_host, leader_port, path))
            raise web.HTTPFound("http://{}:{}{}".format(leader_host, leader_port, path))
        else:
            response = await handler(request)
            return response

    async def index(request):
        return web.Response(text="Hello from {}\r\n".format(identifier))

    app = web.Application(middlewares=[redirect_to_leader])
    app.router.add_get('/test', index)
    web.run_app(app, host='0.0.0.0', port=server_port)


if __name__ == "__main__":
    main()
