from os import environ
from os.path import join

import pytest
from owmeta_pytest_plugin import bundle_fixture_helper


movement_bundle = pytest.fixture(bundle_fixture_helper('openworm/owmeta-movement-schema'))

environ['HTTPS_PYTEST_FIXTURES_CERT'] = join('tests', 'cert.pem')
environ['HTTPS_PYTEST_FIXTURES_KEY'] = join('tests', 'key.pem')
