import os
from os.path import join as p
from unittest.mock import Mock
import shutil

from owmeta_movement.zenodo import ZenodoFilePathProvider
#from owmeta_core.capabilities import FilePathProvider
import pytest
import requests


@pytest.mark.inttest
def test_provides_to(tmp_path, https_server):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    os.mkdir(p(https_server.base_directory, 'record'))
    session = requests.Session()
    https_server.trust_server(session)
    cut = ZenodoFilePathProvider(tmp_path, lambda: session)
    shutil.copyfile(p('tests', 'testdata', 'zenodo_record_20210122.html'),
                    p(https_server.base_directory, 'record', '4074963'))
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.return_value = None
    assert cut.provides_to(ob)


@pytest.mark.inttest
def test_provides_to_no_file_attr(tmp_path, https_server):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    os.mkdir(p(https_server.base_directory, 'record'))
    session = requests.Session()
    https_server.trust_server(session)
    cut = ZenodoFilePathProvider(tmp_path, lambda: session)
    shutil.copyfile(p('tests', 'testdata', 'zenodo_record_20210122.html'),
                    p(https_server.base_directory, 'record', '4074963'))
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.side_effect = AttributeError
    assert cut.provides_to(ob)


@pytest.mark.inttest
def test_provides_to_fail_not_found(tmp_path, https_server):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    os.mkdir(p(https_server.base_directory, 'record'))
    session = requests.Session()
    https_server.trust_server(session)
    cut = ZenodoFilePathProvider(tmp_path, lambda: session)
    shutil.copyfile(p('tests', 'testdata', 'zenodo_record_20210122.html'),
                    p(https_server.base_directory, 'record', '4074963'))
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074962
    ob.zenodo_file_name.return_value = None
    assert cut.provides_to(ob) is None


@pytest.mark.inttest
def test_provides_to_file_fail_not_found(tmp_path, https_server):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    os.mkdir(p(https_server.base_directory, 'record'))
    session = requests.Session()
    https_server.trust_server(session)
    cut = ZenodoFilePathProvider(tmp_path, lambda: session)
    shutil.copyfile(p('tests', 'testdata', 'zenodo_record_20210122.html'),
                    p(https_server.base_directory, 'record', '4074963'))
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.return_value = 'CeMEE_MWT_MA.tar.gz'
    assert cut.provides_to(ob) is None


@pytest.mark.inttest
def test_provides_to_file(tmp_path, https_server):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    session = requests.Session()
    https_server.trust_server(session)
    cut = ZenodoFilePathProvider(tmp_path, lambda: session)

    filesdir = p(https_server.base_directory, 'record', '4074963', 'files')
    os.makedirs(filesdir)
    file_name = p(filesdir, 'CeMEE_MWT_MA.tar.gz')
    with open(file_name, 'w') as f:
        f.write('blah')
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.return_value = 'CeMEE_MWT_MA.tar.gz'
    assert cut.provides_to(ob)
