"""look.py's remote-host guard: the decision is pure (injected resolver), no network."""
import look
import pytest


def res(*addrs):
    return lambda host: list(addrs)


@pytest.mark.parametrize("addr", [
    "127.0.0.1", "192.168.86.31", "10.1.2.3", "172.16.0.1", "172.31.255.254",
    "::1", "fd00::1", "fe80::1", "::ffff:192.168.1.5",
])
def test_local_addresses(addr):
    assert look._is_local_host([addr])


@pytest.mark.parametrize("addr", ["8.8.8.8", "172.32.0.1", "2606:4700::1111", "::ffff:8.8.8.8", "not-an-ip"])
def test_public_addresses(addr):
    assert not look._is_local_host([addr])


@pytest.mark.parametrize("addrs", [[], ["192.168.1.1", "8.8.8.8"]], ids=["empty", "mixed-private-and-public"])
def test_empty_or_mixed_is_not_local(addrs):
    assert not look._is_local_host(addrs)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:1234/v1", "http://192.168.86.31:1234/v1", "http://10.0.0.5/v1",
    "http://172.20.0.2:11434/v1", "http://[::1]:1234/v1", "http://[fd00::5]:1234/v1",
])
def test_local_url_accepted(url):
    assert look._check_remote(url, False, lambda h: [h]) is None


def test_public_ip_refused_and_http_plain_too():
    msg = look._check_remote("http://8.8.8.8:1234/v1", False, lambda h: [h])
    assert msg and "--allow-remote" in msg


def test_name_resolving_public_refused():
    assert look._check_remote("https://api.example.com/v1", False, res("93.184.216.34"))


def test_name_resolving_private_accepted():
    assert look._check_remote("http://lmstudio.lan:1234/v1", False, res("192.168.86.31")) is None


def test_unresolved_name_refused():
    assert look._check_remote("http://nope.invalid/v1", False, res())


def test_mixed_private_and_public_refused():
    assert look._check_remote("http://dual.example/v1", False, res("192.168.1.2", "8.8.8.8"))


def test_allow_remote_accepts_a_public_url():
    assert look._check_remote("http://8.8.8.8/v1", True, lambda h: [h]) is None


@pytest.mark.parametrize("url, remote", [("http://8.8.8.8/v1", True), ("http://127.0.0.1/v1", False)],
                         ids=["public", "loopback"])
def test_is_remote(url, remote):
    assert look.is_remote(url, lambda h: [h]) is remote


def test_no_host_is_an_error():
    assert look._check_remote("not a url", True, res("127.0.0.1"))


@pytest.fixture
def png(tmp_path):
    p = tmp_path / "cv-p1.png"
    p.write_bytes(look.PNG_MAGIC + b"x")
    return p


def test_main_refuses_before_any_request(png, capsys, monkeypatch):
    def no_network(*a, **k):
        raise AssertionError("network call attempted")

    monkeypatch.setattr(look, "_open", no_network)
    monkeypatch.setattr(look.urllib.request, "urlopen", no_network)
    monkeypatch.setattr(look, "ask", no_network)
    with pytest.raises(SystemExit) as e:
        look.main(["--base-url", "http://8.8.8.8:1/v1", "--model", "m", str(png)])
    assert e.value.code == 2
    assert "--allow-remote" in capsys.readouterr().err


def test_allow_remote_lets_main_reach_the_request(png, capsys, monkeypatch):
    reached = []

    def fake_ask(*a, **k):
        reached.append(a[0])
        raise RuntimeError("stop here")

    monkeypatch.setattr(look, "ask", fake_ask)
    with pytest.raises(SystemExit):
        look.main(["--allow-remote", "--base-url", "http://8.8.8.8:1/v1", "--model", "m", str(png)])
    assert reached == ["http://8.8.8.8:1/v1"]
    assert "WARNING" in capsys.readouterr().err


# --- proxy environment variables: local requests bypass them, --allow-remote keeps them ---

def _dead_proxy(monkeypatch):
    for k in ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(k, "http://127.0.0.1:9")  # discard port: nothing listens
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)


@pytest.mark.integration  # real localhost socket
def test_local_request_ignores_proxy_env(monkeypatch):
    import http.server
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        _dead_proxy(monkeypatch)
        assert look.http_json(f"http://127.0.0.1:{srv.server_port}/v1/models", None, 5) == {"ok": True}
    finally:
        srv.shutdown()
        srv.server_close()


def test_allow_remote_path_keeps_default_proxy_honouring_urlopen(monkeypatch):
    _dead_proxy(monkeypatch)
    monkeypatch.setattr(look, "_resolve", lambda h: ["8.8.8.8"])
    calls = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        return Resp()

    monkeypatch.setattr(look.urllib.request, "urlopen", fake_urlopen)
    assert look.http_json("http://example.invalid/v1/models", None, 5) == {}
    assert calls == ["http://example.invalid/v1/models"]
