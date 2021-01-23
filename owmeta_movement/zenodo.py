from contextlib import contextmanager
import logging
from os import makedirs
from os.path import join as p, isfile
import re
import shutil

from bs4 import BeautifulSoup
from owmeta_core.data_trans.local_file_ds import LocalFileDataSource
from owmeta_core.capabilities import FilePathProvider
from owmeta_core.context import ClassContext
from owmeta_core.dataobject import DatatypeProperty
import requests

from . import CONTEXT

L = logging.getLogger(__name__)

SCHEMA_URL = 'http://schema.openworm.org/2020/07/sci/bio/movement/zenodo'

CONTEXT = ClassContext(ident=SCHEMA_URL,
        imported=(CONTEXT,),
        base_namespace=SCHEMA_URL + '#')


class ZenodoFilePathProvider(FilePathProvider):
    '''
    Provides files by downloading them from Zonodo.
    '''

    def __init__(self, base_directory, session_provider=None):
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
        if not base_directory:
            raise ValueError('Expected a directory path name for `base_directory`')

        if session_provider is None:
            session_provider = lambda: requests.Session()
        self._session_provider = session_provider
        self._base_directory = base_directory

    def provides_to(self, ob):
        try:
            zenodo_id = ob.zenodo_id()
        except AttributeError:
            L.debug('Missing zenodo_id property for %s. Cannot download any files', ob)
            return None

        try:
            file_name = ob.zenodo_file_name()
        except AttributeError:
            file_name = None
            L.debug('Missing zenodo_file_name for %s. Will download all files in the'
                    ' record...', ob)

        if not zenodo_id:
            L.debug('zenodo_id value is invalid: %s', zenodo_id)
            return None

        if file_name is not None and not file_name:
            L.debug('zenodo_file_name value is invalid: %s', file_name)
            return None

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
        if response.status_code == 200:
            return _ZenodoFileProvider(self._session_provider, self._base_directory,
                    file_name, zenodo_base_url, zenodo_id)
        return None


class _ZenodoFileProvider(FilePathProvider):
    def __init__(self, session_provider, base_directory, file_name, zenodo_base_url, zenodo_id):
        self.file_name = file_name
        self.zenodo_base_url = zenodo_base_url
        self.zenodo_id = zenodo_id
        self._session_provider = session_provider
        self._base_directory = base_directory

    def file_path(self):
        recorddir = p(self.base_directory, str(self.zenodo_id))
        makedirs(recorddir, exist_ok=True)

        # May re-evaluate this for resilence  -- as it is, we could fail part-way
        # through and have to redo everything
        if self.file_name:
            files = [self.file_name]
        else:
            # Yeah, I know they have an API. Don't care.
            session = self._session_provider()
            files = []
            with session.get(_record_url(self.zenodo_base_url, self.zenodo_id),
                    stream=True) as response:
                soup = BeautifulSoup(response.raw, 'html.parser')
                re_safe_id = re.escape(self.zenodo_id)
                file_ref_re = re.compile(rf'/record/{re_safe_id}/files/(.*)\?download=1')
                link_elems = soup.find_all(href=file_ref_re)
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
                with self._download_from_zenodo(file_name) as response:
                    with open(dest_file_name, 'wb') as dest_file:
                        # Zenodo seems to assign a distinct record ID for each version of a
                        # record, so we shouldn't have to worry about conflicts here
                        shutil.copyfileobj(response.raw, dest_file)
        return recorddir

    def _download_from_zenodo(self, file_name):
        '''
        Download a file from zenodo.

        The response should be used in a context manager to ensure it is closed properly.

        Parameters
        ----------
        file_name : str
            The file name for
        session : requests.sessions.Session, optional
            Session to use for requests. If omitted, a basic one will be created
            automatically

        Yields
        ------
        requests.Response
            A streaming response for the file from Zenodo.
        '''
        base_url = self.zenodo_base_url or 'https://zenodo.org'
        file_url = _file_url(base_url, self.zenodo_id, file_name)
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

    zenodo_base_url = DatatypeProperty(__doc__='Base Zenodo URL. Should use the well-known'
            ' site URL if this property is unavailable')
    zenodo_id = DatatypeProperty(__doc__='Record ID from Zenodo')
    zenodo_file_name = DatatypeProperty(__doc__='Name of a file in a Zenodo record in'
            ' `zenodo_id`')

    unmapped = False

    @contextmanager
    def download_from_zenodo(self, file_name, session=None):
        '''
        Download a file from zenodo.

        The response should be used in a context manager to ensure it is closed properly.

        Parameters
        ----------
        file_name : str
            The file name for
        session : requests.sessions.Session, optional
            Session to use for requests. If omitted, a basic one will be created
            automatically

        Yields
        ------
        requests.Response
            A streaming response for the file from Zenodo.
        '''
        base_url = self.zenodo_base_url() or 'https://zenodo.org'
        zenodo_id = self.zenodo_id()
        file_url = f'{base_url}/record/{zenodo_id}/files/{file_name}?download=1'
        if session is None:
            session = requests.sessions.Session()
        with session.get(file_url, stream=True) as response:
            yield response
