import os
from os.path import join as p
from unittest.mock import Mock
import shutil
import pytest

from owmeta_core.datasource_loader import LoadFailed
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


def test_load_file(zenodo_dir_loader):
    cut, https_server = zenodo_dir_loader
    filesdir = p(https_server.base_directory, 'record', '4074963', 'files')
    os.makedirs(filesdir)
    target_file_name = 'CeMEE_MWT_MA.tar.gz'
    file_name = p(filesdir, target_file_name)
    with open(file_name, 'w') as f:
        f.write('blah')
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.return_value = target_file_name
    dsdir = cut.load(ob)
    with open(p(dsdir, target_file_name), 'r') as f:
        assert f.read() == 'blah'


def test_load_some_files(tmp_path, https_server):
    '''
    Loads any files available--no error is thrown if some are absent.
    '''
    recorddir = p(https_server.base_directory, 'record')
    os.mkdir(recorddir)
    shutil.copyfile(p('tests', 'testdata', 'zenodo_record_20210122.html'),
                    p(recorddir, '4074963.html'))

    def handler(server_data):
        class handler_class(server_data.basic_handler):
            def do_GET(self):
                if self.path.endswith('4074963'):
                    self.handle_request(200)
                    with open(p(recorddir, '4074963.html'), 'rb') as f:
                        shutil.copyfileobj(f, self.wfile)
                else:
                    super().do_GET()
        return handler_class
    https_server.make_server(handler)
    https_server.restart()
    session = requests.Session()
    https_server.trust_server(session)
    cut = ZenodoRecordDirLoader(tmp_path, lambda: session)
    filesdir = p(https_server.base_directory, 'record', '4074963', 'files')
    os.makedirs(filesdir)
    target_file_name = 'CeMEE_MWT_MA.tar.gz'
    file_name = p(filesdir, target_file_name)
    with open(file_name, 'w') as f:
        f.write('blah')
    ob = Mock()
    ob.zenodo_base_url.return_value = https_server.url
    ob.zenodo_id.return_value = 4074963
    ob.zenodo_file_name.return_value = None
    with pytest.raises(LoadFailed):
        cut.load(ob)


@pytest.mark.inttest
def test_load_real():
    '''
    Test actually loading from Zenodo
    '''


@pytest.fixture
def zenodo_dir_loader(tmp_path, https_server):
    session = requests.Session()
    https_server.trust_server(session)
    return ZenodoRecordDirLoader(tmp_path, lambda: session), https_server
