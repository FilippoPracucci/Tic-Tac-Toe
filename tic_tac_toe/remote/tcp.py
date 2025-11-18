from tic_tac_toe.remote import Connection, Server, ConnectionEvent, ServerEvent, Address
from tic_tac_toe.log import logger
import socket
import threading

class TcpConnection(Connection):
    def __init__(self, socket: socket.socket, callback=None):
        self.__socket = socket
        self.__local_address = Address(*self.__socket.getsockname())
        self.__remote_address = Address(*self.__socket.getpeername())
        self.__notify_closed = False
        self.__callback = callback
        self.__receiver_thread = threading.Thread(target=self.__handle_incoming_messages, daemon=True)
        if self.__callback:
            self.__receiver_thread.start()

    @property
    def local_address(self) -> Address:
        return self.__local_address

    @property
    def remote_address(self) -> Address:
        return self.__remote_address

    @property
    def callback(self):
        return self.__callback or (lambda *_: None)
    
    @callback.setter
    def callback(self, value):
        if self.__callback:
            raise ValueError("Callback can only be set once")
        self.__callback = value
        if value:
            self.__receiver_thread.start()

    @property
    def closed(self):
        return self.__socket._closed
    
    def send(self, message):
        if not isinstance(message, bytes):
            message = message.encode()
            message = int.to_bytes(len(message), 2, 'big') + message
        self.__socket.sendall(message)
        logger.debug(f"Sent {message!r} to all")

    def receive(self):
        length = int.from_bytes(self.__socket.recv(2), 'big')
        if length == 0:
            return None
        payload = self.__socket.recv(length).decode()
        logger.debug(f"Received {length} bytes: {payload}")
        return payload
    
    def close(self):
        self.__socket.close()
        if not self.__notify_closed:
            self.on_event(ConnectionEvent.CLOSE)
            self.__notify_closed = True

    def __handle_incoming_messages(self):
        try:
            while not self.closed:
                message = self.receive()
                if message is None:
                    break
                self.on_event(ConnectionEvent.MESSAGE, message)
        except Exception as e:
            if self.closed and isinstance(e, OSError):
                return # silently ignore error, because this is simply the socket being closed locally
            self.on_event(ConnectionEvent.ERROR, error=e)
        finally:
            self.close()

    def on_event(self, event: ConnectionEvent, payload: str=None, connection: 'Connection'=None, error: Exception=None):
        if connection is None:
            connection = self
        self.callback(event, payload, connection, error)

class TcpServer(Server):
    def __init__(self, port, callback=None):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._address = Address.local_port_on_any_interface(port)
        self.__socket.bind(self._address.as_tuple())
        logger.debug(f"Bind TCP socket to {self.__socket.getsockname()}")
        self.__listener_thread = threading.Thread(target=self.__handle_incoming_connections, daemon=True)
        self._connections = {}
        self.__callback = callback
        if self.__callback:
            self.__listener_thread.start()

    @property
    def address(self) -> Address:
        return Address(*self.__socket.getsockname())
    
    @property
    def connections(self) -> dict:
        return self._connections

    @property
    def callback(self):
        return self.__callback or (lambda *_: None)
    
    @callback.setter
    def callback(self, value):
        if self.__callback:
            raise ValueError("Callback can only be set once")
        self.__callback = value
        if value:
            self.__listener_thread.start()
    
    def __handle_incoming_connections(self):
        self.__socket.listen()
        self.on_event(ServerEvent.LISTEN, address=self._address)
        try:
            while not self.__socket._closed:
                socket, address = self.__socket.accept()
                connection = TcpConnection(socket)
                self._connections[address] = connection
                self.on_event(ServerEvent.CONNECT, connection, address)
        except ConnectionAbortedError as e:
            pass # silently ignore error, because this is simply the socket being closed locally
        except Exception as e:
            self.on_event(ServerEvent.ERROR, error=e)
        finally:
            self.on_event(ServerEvent.STOP)

    def on_event(self, event: str, connection: Connection=None, address: Address=None, error: Exception=None):
        self.__callback(event, connection, address, error)

    def close(self):
        self.__socket.close()

class TcpClient(TcpConnection):
    def __init__(self, server_address: Address, callback=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(Address.local_port_on_any_interface(0).as_tuple())
        logger.debug(f"Bind TCP socket to {sock.getsockname()}")
        sock.connect(server_address.as_tuple())
        logger.debug(f"Connect to server at address '{server_address}'")
        super().__init__(sock, callback)
