import socket
from typing import Protocol, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

@dataclass(unsafe_hash=True)
class Address:
    host: str = field()
    port: int

    def __post_init__(self):
        self._ip = None
        if isinstance(self.port, str):
            self.port = int(self.port)
        assert 0 <= self.port <= 65535, "Port number must be between 0 and 65535"
        self.host = (self.host or '0.0.0.0').strip()

    def __str__(self):
        return f"{self.host}:{self.port}"

    def __repr__(self):
        return f"{type(self).__name__}(host={self.host}, ip={self.ip}, port={self.port})"

    @property
    def ip(self) -> str:
        if self._ip is None:
            self._ip = socket.gethostbyname(self.host)
        return self._ip

    def equivalent_to(self, other: 'Address') -> bool:
        return self.ip == other.ip and self.port == other.port

    @classmethod
    def parse(cls, address: str) -> 'Address':
        host, port = address.split(":")
        return cls(host, int(port))

    @classmethod
    def local_port_on_any_interface(cls, port: int) -> 'Address':
        return cls("0.0.0.0", port)

    @classmethod
    def localhost(cls, port: int) -> 'Address':
        return cls("127.0.0.1", port)

    @classmethod
    def any_local_port(cls) -> 'Address':
        return cls("", 0)

    def as_tuple(self) -> Tuple:
        return self.ip, self.port

class ConnectionEvent(Enum):
    MESSAGE = 0
    CLOSE = 1
    ERROR = 2

    @classmethod
    def all(cls) -> Set['ConnectionEvent']:
        return set(cls.__members__.values())

class Connection(Protocol):

    @property
    def local_address(self) -> Address:
        ...

    @local_address.setter
    def local_address(self, address: Address):
        ...

    @property
    def remote_address(self) -> Address:
        ...

    @remote_address.setter
    def remote_address(self, address: Address):
        ...


    def send(self, payload: bytes | str):
        ...

    def receive(self, decode: bool=True):
        ...

    def close(self):
        ...

    def __enter__(self):
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        ...

class ServerEvent(Enum):
    LISTEN = 0
    CONNECT = 1
    STOP = 2
    ERROR = 3

    @classmethod
    def all(cls) -> Set['ServerEvent']:
        return set(cls.__members__.values())

class Server(Protocol):
    def __init__(self, port: int):
        ...

    def listen(self) -> Connection:
        ...

    def receive(self, decode: bool=True) -> Tuple[str | bytes | None, Address | None]:
        ...

    def send(self, address: Address, payload: bytes | str):
        ...

    def __enter__(self):
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        ...

    def close(self):
        ...
