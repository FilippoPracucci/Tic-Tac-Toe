import socket
from typing import Protocol, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

@dataclass(unsafe_hash=True)
class Address:
    """Represent a network address consisting of a host and a port.

    :param host: The hostname of the endpoint.
    :param port: The numeric port of the endpoint.
    """

    host: str = field()
    port: int

    def __post_init__(self) -> None:
        self._ip = None
        if isinstance(self.port, str):
            self.port = int(self.port)
        assert 0 <= self.port <= 65535, "Port number must be between 0 and 65535"
        self.host = (self.host or '0.0.0.0').strip()

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(host={self.host}, ip={self.ip}, port={self.port})"

    @property
    def ip(self) -> str:
        """Resolve and return the host's IPv4 address.

        :return: The resolved IPv4 address of the host as a string.
        """
        if self._ip is None:
            self._ip = socket.gethostbyname(self.host)
        return self._ip

    def equivalent_to(self, other: 'Address') -> bool:
        """Return whether two addresses resolve to the same endpoint.

        :param other: The :class:`Address` to compare with this address.
        :return: `True` when both the IP and port match, `False` otherwise.
        """
        return self.ip == other.ip and self.port == other.port

    @classmethod
    def parse(cls, address: str) -> 'Address':
        """Parse a `host:port` string into an address.

        :param address: The `host:port` string.
        :return: The parsed network :class:`Address`.
        """
        host, port = address.split(":")
        return cls(host, int(port))

    @classmethod
    def local_port_on_any_interface(cls, port: int) -> 'Address':
        """Create an address bound to every local network interface.

        :param port: The port on which to bind.
        :return: The :class:`Address` created using the wildcard host and the given port.
        """
        return cls("0.0.0.0", port)

    @classmethod
    def localhost(cls, port: int) -> 'Address':
        """Create an address bound to the localhost.

        :param port: The port on which to bind.
        :return: The :class:`Address` created using the localhost and the given port.
        """
        return cls("127.0.0.1", port)

    @classmethod
    def any_local_port(cls) -> 'Address':
        """Create an address requesting an available local port.

        :return: The wildcard :class:`Address` with port zero.
        """
        return cls("", 0)

    def as_tuple(self) -> Tuple:
        """Return the address in the tuple format expected by sockets.

        :return: The resolved IP address and port as a tuple `(ip, port)`.
        """
        return self.ip, self.port

class ConnectionEvent(Enum):
    """Enumeration of events emitted while handling a network connection."""

    MESSAGE = 0
    CLOSE = 1
    ERROR = 2

    @classmethod
    def all(cls) -> Set['ConnectionEvent']:
        """Returns a set containing all the connection events.

        :return: The set of all the :class:`ConnectionEvent` values.
        """
        return set(cls.__members__.values())

class Connection(Protocol):
    """Interface for a bidirectional network connection."""

    @property
    def local_address(self) -> Address:
        """Return the local endpoint of the connection.

        :return: The local :class:`Address` of the connection.
        """
        ...

    @local_address.setter
    def local_address(self, address: Address):
        """Set the local endpoint of the connection.

        :param address: The local :class:`Address` to set.
        """
        ...

    @property
    def remote_address(self) -> Address:
        """Return the remote endpoint of the connection.

        :return: The remote :class:`Address` of the connection.
        """
        ...

    @remote_address.setter
    def remote_address(self, address: Address):
        """Set the remote endpoint of the connection.

        :param address: The remote :class:`Address` to set.
        """
        ...


    def send(self, payload: bytes | str):
        """Send a message over the connection.

        :param message: The text or bytes payload to send.
        """
        ...

    def receive(self) -> str:
        """Receive and decode one message.

        :return: The decoded message payload, or `None` when an empty frame is received.
        """
        ...

    def close(self) -> None:
        """Close the socket and notify listeners once."""
        ...

    def __enter__(self):
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        ...

class ServerEvent(Enum):
    """Enumeration of events emitted during a server's lifecycle."""

    LISTEN = 0
    CONNECT = 1
    STOP = 2
    ERROR = 3

    @classmethod
    def all(cls) -> Set['ServerEvent']:
        """Returns a set containing all the server events.

        :return: The set of all the :class:`ServerEvent` values.
        """
        return set(cls.__members__.values())

class Server(Protocol):
    """Interface for a network server.

    :param port: The local port to bind the server to.
    """

    def __init__(self, port: int):
        ...

    def listen(self) -> Connection:
        ...

    def receive(self, decode: bool = True) -> Tuple[str | bytes | None, Address | None]:
        ...

    def send(self, address: Address, payload: bytes | str) -> None:
        ...

    def __enter__(self):
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        ...

    def close(self) -> None:
        """Close the listening socket."""
        ...
