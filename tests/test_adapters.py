from hodos.publish import GitHubPagesAdapter, LocalAdapter, NullAdapter, get_adapter


def test_null_adapter_reports_ok_without_writing():
    ok, msg = NullAdapter().publish("reports/index.html", "<html></html>")
    assert ok is True
    assert "reports/index.html" in msg


def test_local_adapter_writes_text_with_lf_endings(tmp_path):
    adapter = LocalAdapter(tmp_path)
    ok, msg = adapter.publish("nested/index.html", "line one\r\nline two\r\n")

    dest = tmp_path / "nested" / "index.html"
    assert ok is True
    assert dest.exists()
    assert dest.read_bytes() == b"line one\nline two\n"


def test_local_adapter_writes_binary_unchanged(tmp_path):
    adapter = LocalAdapter(tmp_path)
    payload = bytes([0, 1, 2, 3, 255])
    ok, _ = adapter.publish("assets/logo.png", payload)

    dest = tmp_path / "assets" / "logo.png"
    assert ok is True
    assert dest.read_bytes() == payload


def test_get_adapter_defaults_to_null():
    assert isinstance(get_adapter(), NullAdapter)
    assert isinstance(get_adapter({}), NullAdapter)
    assert isinstance(get_adapter({"adapter": "nonsense"}), NullAdapter)


def test_get_adapter_local(tmp_path):
    adapter = get_adapter({"adapter": "local", "local": {"root_dir": str(tmp_path)}})
    assert isinstance(adapter, LocalAdapter)
    assert adapter.root == tmp_path.resolve()


def test_get_adapter_github_pages_falls_back_without_token(monkeypatch):
    monkeypatch.delenv("HODOS_GITHUB_TOKEN", raising=False)
    adapter = get_adapter({"adapter": "github_pages",
                            "github_pages": {"repo_url": "owner/repo"}})
    assert isinstance(adapter, NullAdapter)


def test_github_pages_adapter_requires_repo_url_and_token():
    try:
        GitHubPagesAdapter(repo_url="", token="x")
        assert False, "expected ValueError"
    except ValueError:
        pass

    try:
        GitHubPagesAdapter(repo_url="owner/repo", token="")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_github_pages_adapter_deny_patterns_reject_matching_path():
    import re
    adapter = GitHubPagesAdapter(
        repo_url="owner/repo", token="fake-token",
        deny_patterns=(re.compile(r"^secrets/"),),
    )
    try:
        adapter.publish("secrets/keys.json", "{}")
        assert False, "expected ValueError from deny pattern"
    except ValueError as e:
        assert "secrets/keys.json" in str(e)
