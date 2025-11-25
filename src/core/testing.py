from __future__ import annotations

"""
Compatibility helpers so legacy Flask-style tests can interact with the FastAPI app.
"""

from typing import Any, Dict, Optional, Tuple

from fastapi.testclient import TestClient


class FlaskStyleResponse:
    """Wrapper that mimics Flask's response helpers on top of requests.Response."""

    def __init__(self, response):
        self._response = response

    def get_json(self):
        return self._response.json()

    def get_data(self, as_text: bool = False):
        if as_text:
            return self._response.text
        return self._response.content

    def __getattr__(self, item):
        return getattr(self._response, item)


class _SessionTransaction:
    """Very small stub used by tests that expect Flask's session_transaction."""

    def __enter__(self):
        self.store: Dict[str, Any] = {}
        return self.store

    def __exit__(self, exc_type, exc, tb):
        return False


class FlaskStyleClient:
    """Adapter around TestClient that accepts Flask-style arguments."""

    def __init__(self, client: TestClient):
        self._client = client

    @property
    def cookies(self):
        return self._client.cookies

    def _split_form_and_files(
        self, data: Optional[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Tuple[Any, Any, Optional[str]]]]]:
        if not data:
            return data, None
        files: Dict[str, Tuple[Any, Any, Optional[str]]] = {}
        cleaned: Dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, tuple) and len(value) >= 2 and hasattr(value[0], "read"):
                file_obj = value[0]
                filename = value[1]
                content_type = value[2] if len(value) > 2 else None
                files[key] = (filename, file_obj, content_type)
            else:
                cleaned[key] = value
        return cleaned, files or None

    def _prepare_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        new_kwargs = dict(kwargs)
        query_params = new_kwargs.pop("query_string", None)
        if query_params is not None:
            new_kwargs.setdefault("params", query_params)
        return new_kwargs

    def get(self, url: str, **kwargs):
        prepared = self._prepare_kwargs(kwargs)
        response = self._client.get(url, **prepared)
        return FlaskStyleResponse(response)

    def post(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs):
        prepared = self._prepare_kwargs(kwargs)
        form_data, inferred_files = self._split_form_and_files(data)
        if inferred_files and "files" not in prepared:
            prepared["files"] = inferred_files
        response = self._client.post(url, data=form_data, **prepared)
        return FlaskStyleResponse(response)

    def put(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs):
        prepared = self._prepare_kwargs(kwargs)
        form_data, inferred_files = self._split_form_and_files(data)
        if inferred_files and "files" not in prepared:
            prepared["files"] = inferred_files
        response = self._client.put(url, data=form_data, **prepared)
        return FlaskStyleResponse(response)

    def delete(self, url: str, **kwargs):
        prepared = self._prepare_kwargs(kwargs)
        response = self._client.delete(url, **prepared)
        return FlaskStyleResponse(response)

    def session_transaction(self):
        return _SessionTransaction()

    def __getattr__(self, item):
        return getattr(self._client, item)


class FlaskClientContext:
    """Context manager returned by app.test_client()."""

    def __init__(self, app):
        self._app = app
        self._client: Optional[TestClient] = None

    def __enter__(self):
        self._client = TestClient(self._app)
        self._client.__enter__()
        return FlaskStyleClient(self._client)

    def __exit__(self, exc_type, exc, tb):
        assert self._client is not None
        return self._client.__exit__(exc_type, exc, tb)


def attach_test_client(app):
    """Attach a Flask-style test_client factory onto the FastAPI app."""

    def _factory():
        return FlaskClientContext(app)

    app.test_client = _factory  # type: ignore[attr-defined]
