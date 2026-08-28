from typing import Any, Dict
from collections.abc import Callable
from tic_tac_toe.remote import Connection, Server, ConnectionEvent, ServerEvent, Address
from tic_tac_toe.log import logger
import socket
import threading

class TcpConnection(Connection):
    """Implementation of a TCP connection.

    :param socket: The underlying TCP socket.
    :param callback: The optional function to invoke for connection events.
    """

    def __init__(self, socket: socket.socket, callback: Callable = None):
        self.logger = logger("TcpConnection")
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

    @local_address.setter
    def local_address(self, address: Address):
        self.__local_address = address

    @property
    def remote_address(self) -> Address:
        return self.__remote_address

    @remote_address.setter
    def remote_address(self, address: Address):
        self.__remote_address = address

    @property
    def callback(self) -> Callable:
        """Return the callback to invoke for connection events.
        
        :return: The callback configured for connection events, or a no-op function if none is configured.
        """
        return self.__callback or (lambda *_: None)
    
    @callback.setter
    def callback(self, value: Callable) -> None:
        """Set the event callback and start the thread to receive messages.

        :param value: The callable to invoke for connection events.
        :raise ValueError: If a callback has already been configured.
        """
        if self.__callback:
            raise ValueError("Callback can only be set once")
        self.__callback = value
        if value:
            self.__receiver_thread.start()

    @property
    def closed(self) -> bool:
        """Return whether the underlying socket has been closed.

        :return: ``True`` if the socket is closed, ``False`` otherwise.
        """
        return self.__socket._closed

    def send(self, message: Any) -> None:
        if not isinstance(message, bytes):
            message = message.encode()
            message = int.to_bytes(len(message), 2, 'big') + message
        self.__socket.sendall(message)
        self.logger.debug(f"Sent {message!r} to all")

    def receive(self) -> str:
        length = int.from_bytes(self.__socket.recv(2), 'big')
        if length == 0:
            return None
        payload = self.__socket.recv(length).decode()
        self.logger.debug(f"Received {length} bytes: {payload}")
        return payload
    
    def close(self) -> None:
        self.__socket.close()
        if not self.__notify_closed:
            self.on_event(ConnectionEvent.CLOSE)
            self.__notify_closed = True

    def on_event(self, event: ConnectionEvent, payload: str = None, connection: Connection = None, error: Exception = None) -> None:
        """Trigger the configured callback for a connection event.

        :param event: The :class:`ConnectionEvent`.
        :param payload: The optional message payload.
        :param connection: The optional connection.
        :param error: The optional exception.
        """
        if connection is None:
            connection = self
        self.callback(event, payload, connection, error)

    def __handle_incoming_messages(self) -> None:
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

class TcpServer(Server):
    """Server for accepting and managing TCP connections on a local port.

    :param port: The local port to bind the server to.
    :param callback: The optional function to invoke for server events.
    """

    def __init__(self, port: int, callback: Callable = None):
        self.logger = logger("TcpServer")
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._address = Address.local_port_on_any_interface(port)
        self.__socket.bind(self._address.as_tuple())
        self.logger.debug(f"Bind TCP socket to {self.__socket.getsockname()}")
        self.__listener_thread = threading.Thread(target=self.__handle_incoming_connections, daemon=True)
        self._connections = {}
        self.__callback = callback
        if self.__callback:
            self.__listener_thread.start()

    @property
    def address(self) -> Address:
        """Return the server's address.

        :return: The :class:`Address` of the server.
        """
        return Address(*self.__socket.getsockname())
    
    @property
    def connections(self) -> Dict:
        """Return the connections accepted by the server.
        
        :return: The mapping of remote addresses to the related :class:`TcpConnection`.
        """
        return self._connections

    @property
    def callback(self) -> Callable:
        """Return the callback to invoke for server events.

        :return: The callback configured for server events, or a no-op function if none is configured.
        """
        return self.__callback or (lambda *_: None)
    
    @callback.setter
    def callback(self, value: Callable) -> None:
        """Set the event callback and start the thread to listen for new connections.
        
        :param value: The callable to invoke for server events.
        :raise ValueError: If a callback has already been configured.
        """
        if self.__callback:
            raise ValueError("Callback can only be set once")
        self.__callback = value
        if value:
            self.__listener_thread.start()

    def on_event(self, event: str, connection: Connection = None, address: Address = None, error: Exception = None) -> None:
        """Trigger the configured callback for a server event.

        :param event: The event.
        :param connection: The optional :class:`Connection`.
        :param address: The optional :class:`Address`.
        :param error: The optional :class:`Exception`.
        """
        self.__callback(event, connection, address, error)

    def close(self) -> None:
        self.__socket.close()

    def __handle_incoming_connections(self) -> None:
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

class TcpClient(TcpConnection):
    """Client for connecting to a TCP server.

    :param server_address: The :class:`Address` of the server to connect to.
    :param callback: The optional function to invoke for connection events.
    """

    def __init__(self, server_address: Address, callback: Callable = None):
        self.logger = logger("TcpClient")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(Address.local_port_on_any_interface(0).as_tuple())
        self.logger.debug(f"Bind TCP socket to {sock.getsockname()}")
        sock.connect(server_address.as_tuple())
        self.logger.debug(f"Connect to server at address '{server_address}'")
        super().__init__(sock, callback)
