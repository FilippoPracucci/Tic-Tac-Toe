import unittest
from tic_tac_toe.remote.tcp import *
from typing import Optional
from tic_tac_toe.log import logging


class BaseTcpTest(unittest.TestCase):
    TEST_PORT = 54321
    server_address = Address('localhost', TEST_PORT)
    message1 = "Hello, World!"
    message2 = "Goodbye, World!"
    server: Optional[TcpServer] = None
    size_before = 0

    @classmethod
    def server_callback(cls, event, connection=None, address=None, error=None):
        logging.debug(f"Server Event: {event}, Address: {address}, Error: {error}")

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = TcpServer(cls.TEST_PORT, callback=cls.server_callback)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server is not None:
            cls.server.close()

    def _wait_connection_put(self):
        while (self.server.connections.__len__().__eq__(self.size_before)):
            ...

    def assertIsLocalEndpoint(self, address: Address):
        self.assertIn(address.ip, {'localhost', '127.0.0.1', '0.0.0.0'})
        self.assertIn(address.port, range(1, 1 << 16))


class TestTcpClientAndServer(BaseTcpTest):
    def test_server_is_initially_bound(self):
        self.assertEqual(self.server.address, Address('0.0.0.0', self.TEST_PORT))

    def test_client_is_initially_bound(self):
        client = TcpClient(self.server_address)
        with client:
            self.assertTrue(client.remote_address.equivalent_to(self.server_address))
            self.assertIsLocalEndpoint(client.local_address)

    def test_communication(self):
        self.size_before = self.server.connections.__len__()
        client1 = TcpClient(self.server_address)
        with client1:
            client1.send(self.message1)
            self._wait_connection_put()
            session1: TcpConnection = self.server.connections[client1.local_address.as_tuple()]
            with session1:
                message = session1.receive()
                self.assertEqual(self.message1, message)
            self.size_before = self.server.connections.__len__()
            client2 = TcpClient(self.server_address)
            with client2:
                client2.send(self.message2)
                self._wait_connection_put()
                session2: TcpConnection = self.server.connections.get(client2.local_address.as_tuple())
                with session2:
                    message = session2.receive()
                    self.assertEqual(self.message2, message)

class TestTcpServerListening(BaseTcpTest):
    def test_server_listening(self):
        self.size_before = self.server.connections.__len__()
        client = TcpClient(self.server_address)
        with client:
            client.send(self.message1)
            self._wait_connection_put()
            server_session: TcpConnection = self.server.connections[client.local_address.as_tuple()]
            with server_session:
                self.assertEqual(server_session.remote_address.port, client.local_address.port)
                self.assertEqual(server_session.receive(), self.message1)
                server_session.send(self.message2)
                self.assertEqual(client.receive(), self.message2)
