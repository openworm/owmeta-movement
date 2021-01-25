from contextlib import contextmanager
import logging
from os import makedirs
from os.path import join as p, isfile
import re
import shutil

from bs4 import BeautifulSoup
from owmeta_core.data_trans.local_file_ds import LocalFileDataSource
from owmeta_core.context import ClassContext
from owmeta_core.datasource_loader import DataSourceDirLoader, LoadFailed
from owmeta_core.datasource import Informational
import requests

from . import CONTEXT

L = logging.getLogger(__name__)

SCHEMA_URL = 'http://schema.openworm.org/2020/07/sci/bio/movement/zenodo'

CONTEXT = ClassContext(ident=SCHEMA_URL,
        imported=(CONTEXT,),
        base_namespace=SCHEMA_URL + '#')


class ZenodoRecordDirLoader(DataSourceDirLoader):
    '''
    Provides files by downloading them from Zonodo.
    '''

    def __init__(self, base_directory, session_provider=None, **kwargs):
        '''
        Parameters
        ----------
        base_directory : str
            Path to a directory where files will be saved when requested. An attempt will
            be made to create the directory if it does not already exist. The files
            created in this directory may be reused by other instances *of the same
            version* of this class.
        session_provider : callable, optional
            Should return a requests.Session for the sake of making requests to Zenodo. By
            default, will use a new session for every request
        '''
        super().__init__(base_directory=base_directory, **kwargs)

        if session_provider is None:
            session_provider = lambda: requests.Session()
        self._session_provider = session_provider

    def can_load(self, ob):
        try:
            zenodo_id = ob.zenodo_id()
        except AttributeError:
            L.debug('Missing zenodo_id property for %s. Cannot download any files', ob)
            return False

        try:
            file_name = ob.zenodo_file_name()
        except AttributeError:
            file_name = None
            L.debug('Missing zenodo_file_name for %s. Will download all files in the'
                    ' record...', ob)

        if not zenodo_id:
            L.debug('zenodo_id value is invalid: %s', zenodo_id)
            return False

        if file_name is not None and not file_name:
            L.debug('zenodo_file_name value is invalid: %s', file_name)
            return False

        # Check the zenodo file is reachable by try to grab the HEAD response for it
        # zenodo_base_url is entirely optional
        zenodo_base_url_prop = getattr(ob, 'zenodo_base_url', None)
        if zenodo_base_url_prop is not None:
            zenodo_base_url = zenodo_base_url_prop()
        else:
            zenodo_base_url = None
        base_url = zenodo_base_url or 'https://zenodo.org'
        if not file_name:
            url = _record_url(base_url, zenodo_id)
        else:
            url = _file_url(base_url, zenodo_id, file_name)

        session = self._session_provider()
        response = session.head(url)
        return response.status_code == 200

    def load(self, data_source):
        try:
            zenodo_id = str(data_source.zenodo_id())
        except AttributeError:
            raise LoadFailed(data_source, self,
                    'Missing zenodo_id property')

        try:
            file_name = data_source.zenodo_file_name()
        except AttributeError:
            file_name = None
            L.debug('Missing zenodo_file_name for %s. Will download all files in the'
                    ' record...', data_source)
        recorddir = p(self.base_directory, zenodo_id)
        makedirs(recorddir, exist_ok=True)

        zenodo_base_url_prop = getattr(data_source, 'zenodo_base_url', None)
        if zenodo_base_url_prop is not None:
            zenodo_base_url = zenodo_base_url_prop()
        else:
            zenodo_base_url = None
        zenodo_base_url = zenodo_base_url or 'https://zenodo.org'
        # May re-evaluate this for resilence  -- as it is, we could fail part-way
        # through and have to redo everything
        if file_name:
            files = [file_name]
        else:
            # Yeah, I know they have an API. Don't care.
            session = self._session_provider()
            files = []
            with session.get(_record_url(zenodo_base_url, zenodo_id), stream=True) as response:
                soup = BeautifulSoup(response.raw, 'html.parser')
                re_safe_id = re.escape(zenodo_id)
                file_ref_re = re.compile(rf'/record/{re_safe_id}/files/(.*)\?download=1')
                link_elems = soup.find_all(href=file_ref_re)
                if not link_elems:
                    raise LoadFailed(data_source, self, 'Could not find any files')
                for elem in link_elems:
                    md = file_ref_re.match(elem['href'])
                    if md:
                        files.append(md.group(1))
                    else:
                        L.warning('Regular expression does not match twice?? I guess BeautifulSoup4 is broken.')

        for file_name in files:
            dest_file_name = p(recorddir, file_name)
            if isfile(dest_file_name):
                # TODO: check the hash of the file is the one we expect
                pass
            else:
                with self._download_from_zenodo(zenodo_id, file_name, zenodo_base_url) as response:
                    if response.status_code != 200:
                        raise LoadFailed(data_source, self, f'Missing file {file_name}')
                    with open(dest_file_name, 'wb') as dest_file:
                        # Zenodo seems to assign a distinct record ID for each version of a
                        # record, so we shouldn't have to worry about conflicts here
                        shutil.copyfileobj(response.raw, dest_file)
        return recorddir

    @contextmanager
    def _download_from_zenodo(self, zenodo_id, file_name, base_url):
        '''
        Download a file from zenodo.

        The response should be used in a context manager to ensure it is closed properly.

        Parameters
        ----------
        zenodo_id : str
            The Zenodo record ID
        file_name : str
            The file name for
        base_url : str
            The base zenodo URL
        '''
        file_url = _file_url(base_url, zenodo_id, file_name)
        session = self._session_provider()
        with session.get(file_url, stream=True) as response:
            yield response


def _record_url(base_url, zenodo_id):
    return f'{base_url}/record/{zenodo_id}'


def _file_url(base_url, zenodo_id, file_name):
    return f'{base_url}/record/{zenodo_id}/files/{file_name}?download=1'


class ZenodoFileDataSource(LocalFileDataSource):
    '''
    A `LocalFileDataSource` that gets its data from Zenodo.

    Mostly these come from the OpenWorm Movement Database community. There are differences
    between how different zenodo entries in this community package their data, so
    sub-classes should handle the details

    https://zenodo.org/communities/open-worm-movement-database/?page=1&size=20
    '''
    class_context = CONTEXT

    zenodo_base_url = Informational(description='Base Zenodo URL. Should use the well-known'
            ' site URL if this property is unavailable', multiple=False)
    zenodo_id = Informational(description='Record ID from Zenodo', multiple=False)
    zenodo_file_name = Informational(description='Name of a file in a Zenodo record in'
            ' `zenodo_id`', multiple=False)
