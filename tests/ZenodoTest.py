import os
from os.path import join as p
from unittest.mock import Mock
import shutil
import pytest

from owmeta_movement.zenodo import ZenodoRecordDirLoader
import requests


def test_can_load(zenodo_dir_loader):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    cut, https_server = zenodo_dir_loader
    os.mkdir(p(https_server.base_directory, 'record'))
    shutil.copyfile(p('tests', 'testdata', 'zenodo_record_20210122.html'),
                    p(https_server.base_directory, 'record', '4074963'))
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.return_value = None
    assert cut.can_load(ob)


def test_can_load_no_file_attr(zenodo_dir_loader):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    cut, https_server = zenodo_dir_loader
    os.mkdir(p(https_server.base_directory, 'record'))
    shutil.copyfile(p('tests', 'testdata', 'zenodo_record_20210122.html'),
                    p(https_server.base_directory, 'record', '4074963'))
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.side_effect = AttributeError
    assert cut.can_load(ob)


def test_can_load_fail_not_found(zenodo_dir_loader):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    cut, https_server = zenodo_dir_loader
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.return_value = None
    assert not cut.can_load(ob)


def test_can_load_file_fail_not_found(zenodo_dir_loader):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    cut, https_server = zenodo_dir_loader
    recorddir = p(https_server.base_directory, 'record')
    os.mkdir(recorddir)
    shutil.copyfile(p('tests', 'testdata', 'zenodo_record_20210122.html'),
                    p(recorddir, '4074963'))
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.return_value = 'CeMEE_MWT_MA.tar.gz'
    assert not cut.can_load(ob)


def test_can_load_file(zenodo_dir_loader):
    '''
    Test that we provide for a matching record ID with no file name
    '''
    cut, https_server = zenodo_dir_loader

    filesdir = p(https_server.base_directory, 'record', '4074963', 'files')
    os.makedirs(filesdir)
    file_name = p(filesdir, 'CeMEE_MWT_MA.tar.gz')
    with open(file_name, 'w') as f:
        f.write('blah')
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.return_value = 'CeMEE_MWT_MA.tar.gz'
    assert cut.can_load(ob)


def test_load_file(tmp_path, https_server):
    pass


@pytest.fixture
def zenodo_dir_loader(tmp_path, https_server):
    session = requests.Session()
    https_server.trust_server(session)
    return ZenodoRecordDirLoader(tmp_path, lambda: session), https_server
