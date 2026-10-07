import sys
import ctypes
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

try:
    import main_qml
    from PySide6.QtWidgets import QApplication
    from PySide6.QtNetwork import QLocalServer
except Exception:  # pragma: no cover - env without PySide6 / project deps
    main_qml = None
    QApplication = None
    QLocalServer = None


def _ensure_qapp():
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app


@unittest.skipIf(main_qml is None, "main_qml / PySide6 not available")
class SingleInstanceServerNameTests(unittest.TestCase):
    def test_server_name_format_and_stability(self):
        with patch.object(main_qml.getpass, "getuser", return_value="testuser"):
            a = main_qml._single_instance_server_name()
            b = main_qml._single_instance_server_name()
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("MOUSEPRO_instance_"))
        self.assertEqual(len(a), len("MOUSEPRO_instance_") + 16)


class _FakeWinFunc:
    def __init__(self, func):
        self._func = func
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self._func(*args)


@unittest.skipIf(main_qml is None, "main_qml / PySide6 not available")
class TryActivateExistingTests(unittest.TestCase):
    @patch("main_qml.QLocalSocket")
    def test_returns_false_when_not_connected(self, mock_sock_cls):
        sock = MagicMock()
        sock.waitForConnected.return_value = False
        mock_sock_cls.return_value = sock
        self.assertFalse(main_qml._try_activate_existing_instance("pipe_name"))
        sock.write.assert_not_called()

    @patch("main_qml.QLocalSocket")
    def test_returns_true_and_sends_payload_when_connected(self, mock_sock_cls):
        sock = MagicMock()
        sock.waitForConnected.return_value = True
        sock.waitForBytesWritten.return_value = True
        mock_sock_cls.return_value = sock
        self.assertTrue(main_qml._try_activate_existing_instance("pipe_name"))
        sock.connectToServer.assert_called_once_with("pipe_name")
        sock.write.assert_called_once_with(main_qml._SINGLE_INSTANCE_ACTIVATE_MSG)
        sock.disconnectFromServer.assert_called_once()


@unittest.skipIf(main_qml is None, "main_qml / PySide6 not available")
class WindowsSingleInstanceMutexTests(unittest.TestCase):
    def setUp(self):
        main_qml._WINDOWS_SINGLE_INSTANCE_MUTEX_HANDLE = None

    def tearDown(self):
        main_qml._WINDOWS_SINGLE_INSTANCE_MUTEX_HANDLE = None

    def _fake_windll(self, *, handle=100, last_error=0):
        close_handle = MagicMock()
        kernel32 = SimpleNamespace(
            CreateMutexW=_FakeWinFunc(lambda *_args: handle),
            GetLastError=_FakeWinFunc(lambda: last_error),
            CloseHandle=_FakeWinFunc(close_handle),
        )
        return SimpleNamespace(kernel32=kernel32), close_handle

    def test_non_windows_mutex_noops(self):
        with patch.object(main_qml.sys, "platform", "linux"):
            self.assertTrue(main_qml._acquire_windows_single_instance_mutex())

    def test_windows_mutex_records_primary_handle(self):
        windll, close_handle = self._fake_windll(handle=123, last_error=0)

        with (
            patch.object(main_qml.sys, "platform", "win32"),
            patch.object(ctypes, "windll", windll, create=True),
            patch.object(main_qml.atexit, "register") as register,
        ):
            self.assertTrue(main_qml._acquire_windows_single_instance_mutex())

        self.assertEqual(main_qml._WINDOWS_SINGLE_INSTANCE_MUTEX_HANDLE, 123)
        close_handle.assert_not_called()
        register.assert_called_once_with(main_qml._release_windows_single_instance_mutex)

    def test_windows_mutex_rejects_existing_instance(self):
        windll, close_handle = self._fake_windll(
            handle=456,
            last_error=main_qml._WINDOWS_ERROR_ALREADY_EXISTS,
        )

        with (
            patch.object(main_qml.sys, "platform", "win32"),
            patch.object(ctypes, "windll", windll, create=True),
            patch.object(main_qml.atexit, "register") as register,
        ):
            self.assertFalse(main_qml._acquire_windows_single_instance_mutex())

        self.assertIsNone(main_qml._WINDOWS_SINGLE_INSTANCE_MUTEX_HANDLE)
        close_handle.assert_called_once_with(456)
        register.assert_not_called()


@unittest.skipIf(main_qml is None, "main_qml / PySide6 not available")
class SingleInstanceAcquireTests(unittest.TestCase):
    @patch("main_qml._try_activate_existing_instance", return_value=True)
    def test_secondary_instance_returns_exit_zero(self, _):
        app = _ensure_qapp()
        server, code = main_qml._single_instance_acquire(app, "any_name")
        self.assertIsNone(server)
        self.assertEqual(code, 0)

    @patch("main_qml._try_activate_existing_instance", return_value=False)
    @patch("main_qml.QLocalServer.removeServer")
    def test_primary_gets_server_when_listen_succeeds(self, _remove, _try_act):
        mock_server = MagicMock()
        mock_server.listen.return_value = True
        with patch("main_qml.QLocalServer", return_value=mock_server):
            app = _ensure_qapp()
            server, code = main_qml._single_instance_acquire(app, "unique_name")
        self.assertIsNone(code)
        self.assertIs(server, mock_server)
        mock_server.listen.assert_called_once_with("unique_name")

    def test_primary_integration_unique_pipe(self):
        app = _ensure_qapp()
        name = f"MOUSEPRO_unittest_{uuid.uuid4().hex}"
        server, code = main_qml._single_instance_acquire(app, name)
        self.addCleanup(lambda: (server.close(), QLocalServer.removeServer(name)))
        self.assertIsNone(code)
        self.assertIsNotNone(server)
        self.assertTrue(server.isListening())

        server2, code2 = main_qml._single_instance_acquire(app, name)
        self.assertEqual(code2, 0)
        self.assertIsNone(server2)


@unittest.skipIf(main_qml is None, "main_qml / PySide6 not available")
class DrainActivateSocketTests(unittest.TestCase):
    def test_noop_when_sock_is_none(self):
        main_qml._drain_local_activate_socket(None)

    def test_drains_when_sock_present(self):
        mock_sock = MagicMock()
        main_qml._drain_local_activate_socket(mock_sock)
        mock_sock.waitForReadyRead.assert_called_once_with(300)
        mock_sock.readAll.assert_called_once()
        mock_sock.deleteLater.assert_called_once()
