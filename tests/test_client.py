from unittest import mock
from urllib.parse import urlencode

import pytest
import requests_mock
from django.conf import settings
from django.test import override_settings

from django_json_api.client import JSONAPIClient, JSONAPIClientError


@pytest.fixture
def mock_requests():
    with requests_mock.Mocker() as mocker:
        yield mocker


@pytest.fixture
def mock_version():
    with mock.patch("django_json_api.client.__version__") as mock_context:
        mock_context.__str__ = lambda _: "0.1.2"
        yield mock_context


@override_settings(DJANGO_JSON_API_ADDITIONAL_HEADERS={})
def test_jsonapi_client_session_headers(mock_version):
    del settings.DJANGO_JSON_API_ADDITIONAL_HEADERS
    client = JSONAPIClient()
    assert client.session.headers["Accept"] == "application/vnd.api+json"
    assert client.session.headers["Content-Type"] == "application/vnd.api+json"
    assert client.session.headers["User-Agent"] == "JSONAPIClient/0.1.2"

    setattr(
        settings,
        "DJANGO_JSON_API_ADDITIONAL_HEADERS",
        {
            "User-Agent": f"SW_{settings.SERVICE}/JsonAPI",
            "X-SW-service": settings.SERVICE,
        },
    )

    client = JSONAPIClient()
    assert client.session.headers["Accept"] == "application/vnd.api+json"
    assert client.session.headers["Content-Type"] == "application/vnd.api+json"
    assert client.session.headers["User-Agent"] == "SW_test/JsonAPI"
    assert client.session.headers["X-SW-service"] == "test"


def test_jsonapi_client_get_list_default(mock_requests):
    expected_params = {
        "fields[related_records]": "name,other_related",
        "include": "other_related",
    }
    url = f"http://example.com/related-records/?{urlencode(expected_params)}"
    mock_requests.get(url, json={})
    client = JSONAPIClient()
    client.get("related_records")
    assert mock_requests.called
    assert mock_requests.last_request.url == url


def test_jsonapi_client_get_record_default(mock_requests):
    expected_params = {
        "fields[related_records]": "name,other_related",
        "include": "other_related",
    }
    url = f"http://example.com/related-records/42/?{urlencode(expected_params)}"
    mock_requests.get(url, json={})
    client = JSONAPIClient()
    client.get("related_records", resource_id=42)
    assert mock_requests.called
    assert mock_requests.last_request.url == url


def test_jsonapi_client_get_with_include(mock_requests):
    expected_params = {
        "fields[related_records]": "name,other_related",
        "include": "resource1,resource2",
    }
    url = f"http://example.com/related-records/?{urlencode(expected_params)}"
    mock_requests.get(url, json={})
    client = JSONAPIClient()
    client.get("related_records", include=["resource1", "resource2"])
    assert mock_requests.called
    assert mock_requests.last_request.url == url


def test_jsonapi_client_get_with_include_empty(mock_requests):
    expected_params = {
        "fields[related_records]": "name,other_related",
    }
    url = f"http://example.com/related-records/?{urlencode(expected_params)}"
    mock_requests.get(url, json={})
    client = JSONAPIClient()
    client.get("related_records", include=[])
    assert mock_requests.called
    assert mock_requests.last_request.url == url


def test_jsonapi_client_get_with_fields_override_resource_default(mock_requests):
    expected_params = {
        "fields[related_records]": "name",
        "include": "other_related",
    }
    url = f"http://example.com/related-records/?{urlencode(expected_params)}"
    mock_requests.get(url, json="{}")
    client = JSONAPIClient()
    client.get("related_records", fields={"related_records": ["name"]})
    assert mock_requests.called
    assert mock_requests.last_request.url == url


def test_jsonapi_client_get_with_fields_for_related(mock_requests):
    expected_params = {
        "fields[other_related]": "something",
        "fields[related_records]": "name,other_related",
        "include": "other_related",
    }
    url = f"http://example.com/related-records/?{urlencode(expected_params)}"
    mock_requests.get(url, json={})
    client = JSONAPIClient()
    client.get("related_records", fields={"other_related": ["something"], "not_used": []})
    assert mock_requests.called
    assert mock_requests.last_request.url == url


def test_jsonapi_client_get_with_sort(mock_requests):
    expected_params = {
        "fields[related_records]": "name,other_related",
        "include": "other_related",
        "sort": "-name,other_related",
    }
    url = f"http://example.com/related-records/?{urlencode(expected_params)}"
    mock_requests.get(url, json="{}")
    client = JSONAPIClient()
    client.get("related_records", sort=["-name", "other_related"])
    assert mock_requests.called
    assert mock_requests.last_request.url == url


def test_jsonapi_client_get_with_page_size(mock_requests):
    expected_params = {
        "fields[related_records]": "name,other_related",
        "include": "other_related",
        "page[size]": 25,
    }
    url = f"http://example.com/related-records/?{urlencode(expected_params)}"
    mock_requests.get(url, json="{}")
    client = JSONAPIClient()
    client.get("related_records", page_size=25)
    assert mock_requests.called
    assert mock_requests.last_request.url == url


def test_jsonapi_client_get_with_page_number(mock_requests):
    expected_params = {
        "fields[related_records]": "name,other_related",
        "include": "other_related",
        "page[number]": 12,
    }
    url = f"http://example.com/related-records/?{urlencode(expected_params)}"
    mock_requests.get(url, json="{}")
    client = JSONAPIClient()
    client.get("related_records", page_number=12)
    assert mock_requests.called
    assert mock_requests.last_request.url == url


def test_jsonapi_client_get_handles_http_errors(mock_requests):
    expected_params = {
        "include": "other_related",
        "fields[related_records]": "name,other_related",
    }
    mock_requests.register_uri(
        "GET",
        f"http://example.com/related-records/?{urlencode(expected_params)}",
        status_code=400,
        json={"error": "some error"},
    )
    client = JSONAPIClient()
    with pytest.raises(JSONAPIClientError):
        client.get("related_records")
    assert mock_requests.called


def test_jsonapi_get_unresolved_resource():
    client = JSONAPIClient()
    with pytest.raises(JSONAPIClientError, match=r'Cannot resolve resource "unresolvable"'):
        client.get("unresolvable")
