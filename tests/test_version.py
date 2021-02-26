import os
from typing import Generator
from unittest import mock

import pytest
from testfixtures import TempDirectory

from django_json_api.version import version


@pytest.fixture
def temp_dir() -> Generator[TempDirectory, None, None]:
    with TempDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def version_file(temp_dir: TempDirectory) -> Generator[mock.Mock, None, None]:
    version_file_content: bytes = b"0.1.2\n"
    version_file_name: str = "VERSION"

    with mock.patch("django_json_api.version.join") as mock_context:
        temp_dir.write(version_file_name, version_file_content)
        mock_context.return_value = os.path.join(temp_dir.path, version_file_name)
        yield mock_context


def test_version(version_file: mock.Mock) -> None:
    assert version() == "0.1.2"
