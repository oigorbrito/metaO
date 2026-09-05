"""SDK-neutral stdio transport for Codex App Server.

The App Server stdio protocol is newline-delimited JSON-RPC-like messages without
the JSON-RPC version envelope. This transport demultiplexes responses,
notifications and server-to-client requests on a background reader thread so a
running metaO execution can still be interrupted concurrently.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
import json
from queue import Queue
import subprocess
from threading import Condition, Lock, Thread
from typing import Any

from .codex_app_server import CodexAppServerProtocolError, CodexAppServerRpcError


ServerRequestHandler = Callable[[str, Mapping[str, Any] | None], Any]
RpcId = int | str


class _ReaderClosed:
    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error


def _is_rpc_id(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, str))


class CodexAppServerStdioTransport:
    """Own a `codex app-server --stdio` process and expose synchronous RPC calls."""

    def __init__(
        self,
        command: Sequence[str] = ("codex", "app-server", "--stdio"),
        *,
        server_request_handler: ServerRequestHandler | None = None,
        popen_factory: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
        stderr_tail_lines: int = 200,
    ) -> None:
        if not command:
            raise ValueError("Codex App Server command must be non-empty")
        if stderr_tail_lines <= 0:
            raise ValueError("stderr_tail_lines must be positive")
        self._server_request_handler = server_request_handler
        self._write_lock = Lock()
        self._condition = Condition(Lock())
        self._stderr_lock = Lock()
        self._next_id = 1
        self._responses: dict[int, Mapping[str, Any]] = {}
        self._reader_error: BaseException | None = None
        self._notifications: Queue[Mapping[str, Any] | _ReaderClosed] = Queue()
        self._stderr_tail: deque[str] = deque(maxlen=stderr_tail_lines)
        self._process = popen_factory(
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        if self._process.stdin is None or self._process.stdout is None:
            raise CodexAppServerProtocolError("Codex App Server stdio pipes were not created")
        self._reader = Thread(target=self._reader_loop, name="metao-codex-app-server", daemon=True)
        self._reader.start()
        self._stderr_reader = Thread(
            target=self._stderr_loop,
            name="metao-codex-app-server-stderr",
            daemon=True,
        )
        self._stderr_reader.start()

    def _send(self, message: Mapping[str, Any]) -> None:
        encoded = json.dumps(message, separators=(",", ":"), default=str)
        with self._write_lock:
            stdin = self._process.stdin
            if stdin is None or stdin.closed:
                raise CodexAppServerProtocolError("Codex App Server stdin is closed")
            stdin.write(encoded + "\n")
            stdin.flush()

    def _allocate_id(self) -> int:
        with self._condition:
            request_id = self._next_id
            self._next_id += 1
            return request_id

    def request(self, method: str, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        request_id = self._allocate_id()
        message: dict[str, Any] = {"method": method, "id": request_id}
        if params is not None:
            message["params"] = dict(params)
        self._send(message)

        with self._condition:
            while request_id not in self._responses and self._reader_error is None:
                self._condition.wait()
            if request_id not in self._responses:
                error = self._reader_error
                if error is None:
                    raise CodexAppServerProtocolError("Codex App Server reader stopped")
                raise CodexAppServerProtocolError(
                    f"Codex App Server reader stopped: {error}"
                ) from error
            response = self._responses.pop(request_id)

        error = response.get("error")
        if isinstance(error, Mapping):
            code = error.get("code")
            message_value = error.get("message")
            raise CodexAppServerRpcError(
                int(code) if isinstance(code, int) else -32000,
                str(message_value) if message_value is not None else "unknown RPC error",
                error.get("data"),
            )
        result = response.get("result")
        if not isinstance(result, Mapping):
            raise CodexAppServerProtocolError(
                f"Codex App Server {method} returned a non-object result"
            )
        return result

    def notify(self, method: str, params: Mapping[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = dict(params)
        self._send(message)

    def read_notification(self) -> Mapping[str, Any]:
        item = self._notifications.get()
        if isinstance(item, _ReaderClosed):
            if item.error is None:
                raise CodexAppServerProtocolError("Codex App Server stdout closed")
            raise CodexAppServerProtocolError(
                f"Codex App Server reader failed: {item.error}"
            ) from item.error
        return item

    def stderr_tail(self) -> tuple[str, ...]:
        with self._stderr_lock:
            return tuple(self._stderr_tail)

    def _handle_server_request(self, message: Mapping[str, Any]) -> None:
        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params")
        if not _is_rpc_id(request_id) or not isinstance(method, str):
            raise CodexAppServerProtocolError("invalid server request envelope")
        params_mapping = params if isinstance(params, Mapping) else None
        handler = self._server_request_handler
        if handler is None:
            self._send(
                {
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "metaO client has no handler for this server request",
                    },
                }
            )
            return
        try:
            result = handler(method, params_mapping)
        except Exception as exc:
            self._send(
                {
                    "id": request_id,
                    "error": {"code": -32000, "message": str(exc)},
                }
            )
            return
        self._send({"id": request_id, "result": result if result is not None else {}})

    def _reader_loop(self) -> None:
        stdout = self._process.stdout
        assert stdout is not None
        try:
            for raw_line in stdout:
                line = raw_line.strip()
                if not line:
                    continue
                value = json.loads(line)
                if not isinstance(value, Mapping):
                    raise CodexAppServerProtocolError(
                        "Codex App Server emitted a non-object JSON value"
                    )

                has_method = isinstance(value.get("method"), str)
                request_id = value.get("id")
                if has_method and _is_rpc_id(request_id):
                    self._handle_server_request(value)
                    continue
                if isinstance(request_id, int) and not isinstance(request_id, bool):
                    with self._condition:
                        self._responses[request_id] = value
                        self._condition.notify_all()
                    continue
                if has_method:
                    self._notifications.put(value)
                    continue
                raise CodexAppServerProtocolError("unrecognized Codex App Server message")
        except BaseException as exc:
            with self._condition:
                self._reader_error = exc
                self._condition.notify_all()
            self._notifications.put(_ReaderClosed(exc))
            return

        error: BaseException | None = None
        return_code = self._process.poll()
        if return_code not in {None, 0}:
            error = CodexAppServerProtocolError(
                f"Codex App Server exited with status {return_code}"
            )
        with self._condition:
            self._reader_error = error or CodexAppServerProtocolError(
                "Codex App Server stdout closed"
            )
            self._condition.notify_all()
        self._notifications.put(_ReaderClosed(error))

    def _stderr_loop(self) -> None:
        stderr = self._process.stderr
        if stderr is None:
            return
        try:
            for raw_line in stderr:
                line = raw_line.rstrip("\r\n")
                with self._stderr_lock:
                    self._stderr_tail.append(line)
        except Exception as exc:
            with self._stderr_lock:
                self._stderr_tail.append(f"<stderr reader failed: {exc}>")

    def close(self) -> None:
        process = self._process
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def __enter__(self) -> "CodexAppServerStdioTransport":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
