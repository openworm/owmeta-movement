from os import environ
from os.path import join

environ['HTTPS_PYTEST_FIXTURES_CERT'] = join('tests', 'cert.pem')
environ['HTTPS_PYTEST_FIXTURES_KEY'] = join('tests', 'key.pem')
