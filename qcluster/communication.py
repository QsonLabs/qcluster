import aiohttp
import async_timeout

from aiohttp import web
from qcluster import utils


class HTTPCommunicator:
    """
    The Communicator class is designed to be imported and exposes a set of
    functions to communicate with another communicator class. It is
    responsible for maintaining a "Requester" and a "Responder".
    """

    def __init__(self, identifier, listen_port, listen_host="localhost"):
        """
        Creates a new HTTPCommunication object. This will expose higher level
        communications to other parts of the project.

        Args:
            identifier: The identifier of the peer implementing the SDK.
            listen_host: The hostname that will accept inbound messages.
            listen_port: The port that will accept inbound messages.
        """
        self.identifier = identifier
        self.listen_host = listen_host
        self.listen_port = listen_port

        self._requester = _HTTPRequester()
        self._responder = _HTTPResponder(self.listen_host, self.listen_port)

    async def start(self):
        """
        Responsible for formally starting the sub-services used for HTTP
        communication.

        This needs to be called before requests will be accepted.
        """
        await self._responder.start_server()

    async def ping(self, host, port, timeout=1):
        """
        A small ping message will be sent to the desired peer in order to test
        connectivity.

        Args:
            host: The host to ping.
            port: The port to ping.
            timeout: Optional; The maximum time in seconds to wait for a
              response. (Default=1)

        Returns:
            True if the appropriate 'pong' response was received. False if
            there are connectivity issues or a timeout exceeded.
        """
        try:
            response = await self._requester.get(host, port, '/ping', timeout)
            return response.status == 200
        except aiohttp.client_exceptions.ClientConnectorError:
            return False

    async def send_heartbeat(self, to_host, to_port, timeout=1):
        """
        Sends a heartbeat message to a peer.

        Args:
            to_host: The host to send the heartbeat to.
            to_port: The port on the host to send the heartbeat to.
            timeout: Optional; THe maximum time in seconds to wait for a
              response. (Default=1)

        Returns:
            True if the peer acknowledges the heartbeat. False indicates an
            invalid response from the peer or connectivity issues.
        """
        try:
            payload = {'peer_identifier': self.identifier}
            response = await self._requester.post(to_host,
                                                  to_port,
                                                  '/heartbeat',
                                                  payload,
                                                  timeout)
            return response.status == 200
        except aiohttp.client_exceptions.ClientConnectorError:
            return None

    async def register_with(self, host, port, timeout=1):
        """
        Makes a registration message to a peer. The peer will be notified of
        where the current instance can be reached using the member's host
        and port. The member's identifier will also be transmitted.

        Args:
            host: The host to register with.
            port: The port of the host to register with.
            timeout: Optional; The time in seconds to wait for a response.
              (Default=1)

        Returns:
            True if the registration was successful.
        """
        payload = {
            'host': self.listen_host,
            'port': self.listen_port,
            'identifier': self.identifier
        }
        response = await self._requester.post(host,
                                              port,
                                              '/register',
                                              payload,
                                              timeout)
        return response.status == 200

    def set_on_heartbeat(self, on_heartbeat):
        """
        Setter for the callback to be executed on heartbeat events.

        The callback should accept 1 parameter:
            - The identifier of the peer that sent the heartbeat

        The callback should produce a return value in either of the formats:
            - Tuple (bool, any) where the bool indicates success. Additional
              data can be passed as along in the response.
            - bool to indicate success
            - None to indicate failure
            - Any data to indicate success

        Args:
            on_heartbeat: The function to be called.
        """
        self._responder.set_on_heartbeat(on_heartbeat)

    def set_on_register(self, on_register):
        """
        Setter for the callback to be executed on register events.

        The callback should accept 3 parameters:
            - The host of the new peer
            - The port of the new peer
            - The identifier of the new peer

        The callback should produce a return value in either of the formats:
            - Tuple (bool, any) where the bool indicates success. Additional
              data can be passed as along in the response.
            - bool to indicate success
            - None to indicate failure
            - Any data to indicate success

        Args:
            on_register: The function to be called.
        """
        self._responder.set_on_register(on_register)


class _HTTPRequester:
    """
    A Requester object makes HTTP calls to a Responder object by targeting a
    host and a port.
    """
    def __init__(self):
        pass

    async def get(self, host, port, endpoint, timeout=1):
        """
        Makes an HTTP GET request to a specified location.

        Args:
            host: The host to direct the request to.
            port: The port to direct the request to.
            endpoint: The endpoint to target.
            timeout: Optional; The time in seconds to wait for a response.
              (Default=1)

        Returns:
            An awaited session response.

        Raises:
            asyncio.TimeoutError: The request exceeded the timeout duration.
        """
        async with aiohttp.ClientSession() as session:
            url = "http://{}:{}{}".format(host, port, endpoint)
            print("Making GET request to {}".format(url))
            async with async_timeout.timeout(timeout):
                return await session.get(url)

    async def post(self, host, port, endpoint, data, timeout=1):
        """
        Makes an HTTP POST request to a specified location.

        Args:
            host: The host to direct the request to.
            port: The port to direct the request to.
            endpoint: The endpoint to target.
            data: The data to transmit.
            timeout: Optional; The time in seconds to wait for a response.
              (Default=1)

        Returns:
            An awaited session response.

        Raises:
            asyncio.TimeoutError: The request exceeded the timeout duration.
        """
        async with aiohttp.ClientSession() as session:
            url = "http://{}:{}{}".format(host, port, endpoint)
            print("Making POST request to {} with data: {}".format(url, data))
            async with async_timeout.timeout(timeout):
                return await session.post(url, data=data)


class _HTTPResponder:
    """
    A Responder accepts HTTP requests on a specified port.
    """

    def __init__(self, host, port):
        """
        Creates a new HTTP responder.

        Args:
            host: The host to listen on.
            port: The port to listen on.
        """
        self.host = host
        self.port = port

        self.app = web.Application()
        self.app.router.add_get('/ping', self.handle_ping)
        self.app.router.add_post('/heartbeat', self.handle_heartbeat)
        self.app.router.add_post('/register', self.handle_register)
        self.runner = None
        self.site = None

        self.on_heartbeat = None
        self.on_register = None

    async def start_server(self):
        """
        Starts listening on the host and port for HTTP requests.
        """
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = aiohttp.web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

    @staticmethod
    def respond(callback_response):
        success = callback_response[0]
        data = callback_response[1]
        status_code = 200 if success else 400
        if type(data) is dict:
            return web.json_response(data, status=status_code)
        else:
            return web.Response(status=status_code, text=str(data))

    # MARK: handler methods

    async def handle_ping(self, request):
        """
        Handler for the ping endpoint.

        Args:
            request: The aiohttp request object.

        Returns:
            An aiohttp response object.
        """
        return web.Response(status=200, text="pong")

    async def handle_heartbeat(self, request):
        """
        Handler for the heartbeat endpoint. A callback can be set
        to handle specific events.

        Args:
            request: The aiohttp request object.

        Returns:
            An aiohttp response object.
         """
        data = await request.post()
        peer_identifier = data.get('peer_identifier', None)
        if self.on_heartbeat:
            res = await utils.call_callback(self.on_heartbeat,
                                            peer_identifier)
            return self.respond(res)
        return web.Response(status=200)

    async def handle_register(self, request):
        """
        Handler for the register endpoint. A callback can be set
        to handle specific events.

        Args:
            request: The aiohttp request object.

        Returns:
            An aiohttp response object.
        """
        data = await request.post()
        peer_host = data.get('host', None)
        peer_port = data.get('port', None)
        peer_identifier = data.get('identifier', None)
        if self.on_register:
            res = await utils.call_callback(self.on_register,
                                            peer_host,
                                            int(peer_port),
                                            peer_identifier)
            return self.respond(res)
        return web.Response(status=200)

    # MARK: callback registration

    def set_on_heartbeat(self, on_heartbeat):
        """
        Setter for the callback to be executed on heartbeat events.

        The callback should accept 1 parameter:
            - The identifier of the peer that sent the heartbeat

        Args:
            on_heartbeat: The function to be called.
        """
        self.on_heartbeat = on_heartbeat

    def set_on_register(self, on_register):
        """
        Setter for the callback to be executed on register events.

        The callback should accept 3 parameters:
            - The host of the new peer
            - The port of the new peer
            - The identifier of the new peer

        Args:
            on_register: The function to be called.
        """
        self.on_register = on_register
