from contextlib import contextmanager
from os.path import splitext, join as p, isfile
from os import makedirs
import tarfile
import tempfile
import zipfile
import shutil
import json
import io

from owmeta_core.collections import Seq
from owmeta_core.context import ClassContext
from owmeta_core.dataobject import DatatypeProperty
from owmeta_core.json_schema import DataObjectCreator
from pow_zodb.ZODB import register_id_series
import requests
import rdflib

from . import MovementDataSource, CONTEXT


SCHEMA_URL = 'http://schema.openworm.org/2020/07/sci/bio/movement/zenodo'

CONTEXT = ClassContext(ident=SCHEMA_URL,
        imported=(CONTEXT,),
        base_namespace=SCHEMA_URL + '#')


class ZenodoMovementDataSource(MovementDataSource):
    '''
    A `MovementDataSource` that gets its data from Zenodo.

    Mostly these come from the OpenWorm Movement Database community. There are differences
    between how different zenodo entries in this community package their data, so
    sub-classes should handle the details

    https://zenodo.org/communities/open-worm-movement-database/?page=1&size=20
    '''
    class_context = CONTEXT

    zenodo_base_url = DatatypeProperty(__doc__='Base Zenodo URL. Should use the well-known'
            ' site URL if this property is unavailable')
    zenodo_id = DatatypeProperty(__doc__='Record ID from Zenodo')

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


class CeMEEDataSource(ZenodoMovementDataSource):
    '''
    Dealing with the CeMEE Multi-Worm Tracker entries.

    See https://zenodo.org/record/4074963 for more.
    '''
    class_context = CONTEXT

    zenodo_file_name = DatatypeProperty(__doc__='Name of the source file from the Zenodo record')
    sample_zip_file_name = DatatypeProperty(__doc__='Name of the WCON zip within the archive file from the'
            ' Zenodo record. Nominally, corresponds to a sample identified by its strain'
            ' and a timestamp')

    zenodo_file_hash = DatatypeProperty(__doc__='Hash of the contents of the file from'
            ' Zenodo. Formatted like ``<hash-name>:<base64-encoded-hash>``', multiple=True)

    sample_zip_file_hash = DatatypeProperty(__doc__='Hash of the contents of the sample'
            ' ZIP file within the archive from Zenodo. Formatted like'
            ' ``<hash-name>:<base64-encoded-hash>``', multiple=True)

    def populate_from_zenodo(self, schema, session=None, cache_directory=None):
        '''
        Load a data source from a CeMEE record in Zenodo by downloading the WCON data,
        reading in the metadata

        If `zenodo_file_hash` is set, then it will be used for checking any existing file
        in the cache directory.

        Parameters
        ----------
        schema : dict
            `MovementDataSourceTypeCreator`-annotated schema for the WCON data
        session : requests.sessions.Session, optional
            Session to use for requests to Zenodo.
        cache_directory : str, optional
            Directory where files should be saved during extraction. The files created in
            this directory may be reused by other instances *of the same version* of class
            if possible. If not provided, then a temporary directory will be created and
            cleaned up after.

        See Also
        --------
        ZenodoMovementDataSource.download_from_zenodo
        '''
        # Could have opted to make this a classmethod and create the whole datasource, but
        # then we'd be constraining how the datasource gets created and we'd feel
        # compelled to recreate the interface for constructing the object. It's still
        # possible for *someone else* to do those things where it makes more sense (i.e.,
        # a higher-level interface, but then they'll have this method to help them out.

        # Assign these to self just to avoid the
        zenodo_id = self.zenodo_id()
        if not zenodo_id:
            raise Exception('Missing `zenodo_id`')

        zenodo_file_name = self.zenodo_file_name()
        if not zenodo_file_name:
            raise Exception('Missing `zenodo_file_name`')

        sample_zip_file_name = self.sample_zip_file_name()
        if not sample_zip_file_name:
            raise Exception('Missing `sample_zip_file_name`')

        sample_wcon_file_name, ext = splitext(sample_zip_file_name)

        if ext != '.zip':
            raise Exception('Expected sample_zip_file_name to be a zip file name')

        cleanup_dir = False
        if cache_directory is None:
            cache_directory = tempfile.mkdtemp()
            cleanup_dir = True
        mycachedir = p(cache_directory, str(zenodo_id))
        makedirs(mycachedir, exist_ok=True)

        try:
            # May re-evaluate this for resilence  -- as it is, we could fail part-way
            # through and have to redo everything
            cached_tar_file_name = p(mycachedir, zenodo_file_name)
            if isfile(cached_tar_file_name):
                # TODO: check the file is the one we expect
                pass
            else:
                with self.download_from_zenodo(zenodo_file_name) as response:
                    with open(cached_tar_file_name, 'wb') as tar_file:
                        # Zenodo seems to assign a distinct record ID for each version of a
                        # record, so we shouldn't have to worry about conflicts here
                        shutil.copyfileobj(response.raw, tar_file)

            wcon_zip_file_name = p(mycachedir, sample_zip_file_name)
            if isfile(wcon_zip_file_name):
                # TODO: check the file is the one we expect
                pass
            else:
                with tarfile.open(cached_tar_file_name) as tf:
                    tf.extract(sample_zip_file_name, mycachedir)

            with zipfile.ZipFile(wcon_zip_file_name) as zf, \
                    zf.open(sample_wcon_file_name) as wcon:
                wcon_json = json.load(wcon)
                # CeMEE wants to be special... fix up their data
                try:
                    lab = wcon_json['metadata']['lab']
                    if isinstance(lab, str):
                        wcon_json['metadata']['lab'] = {'name': lab}
                except KeyError:
                    pass

                try:
                    software = wcon_json['units']['software']
                    del wcon_json['units']['software']
                    wcon_json.setdefault('metadata', {})['software'] = software
                except KeyError:
                    pass

                try:
                    food = wcon_json['units']['food']
                    del wcon_json['units']['food']
                    wcon_json.setdefault('metadata', {})['food'] = food
                except KeyError:
                    pass
                data = wcon_json['data']
                if isinstance(data, dict) and 'x' not in data:
                    # 'x' is required in a data record, so this was *probably* supposed to
                    # be an array, so let's pretend it is one
                    new_data = dict()
                    for index, record in data.items():
                        # CeMEE uses integers for the IDs, but we need strings
                        record['id'] = str(record['id'])
                        # The times don't match
                        record['t'] = record['t'][0]
                        new_data[int(index)] = record
                    wcon_json['data'] = _SparseList(new_data)
                CeMEEDataSourceCreator(schema).fill_in(self, wcon_json)
        finally:
            if cleanup_dir:
                shutil.rmtree(cache_directory)


_NOPE = object()


class _SparseList(list):
    def __init__(self, base):
        self._base = base

    def __getitem__(self, index):
        try:
            self._base[index]
        except KeyError:
            raise IndexError(index)

    def __setitem__(self, index, value):
        self._base[index] = value

    def __iter__(self):
        index = 0
        maxhits = len(self._base)
        hits = 0
        while True:
            item = self._base.get(index, _NOPE)
            if item is not _NOPE:
                hits += 1
            else:
                item = None
            yield item
            index += 1
            if hits >= maxhits:
                break

    def __str__(self):
        res = io.StringIO()
        res.write('[')
        keys = sorted(self._base.keys())
        last = -1
        first = True
        for m in keys:
            if m - last > 1:
                if not first:
                    res.write(',')
                res.write(' ')
            if m > 0:
                res.write(', ')
            res.write(str(self._base[m]))
            first = False
            last = m
        res.write(']')
        return res.getvalue()

    def __repr__(self):
        return f'_SparseList({self._base})'


class CeMEEDataSourceCreator(DataObjectCreator):
    '''
    Creates MovementDataSources from CeMEE Zenodo records
    '''
    def make_instance(self, owm_type):
        if issubclass(owm_type, MovementDataSource):
            return super().make_instance(CeMEEDataSource)
        return super().make_instance(owm_type)

    def begin_sequence(self, schema):
        path = self.path_stack
        if len(path) == 1 and path[0] == 'data':
            return Seq.contextualize(self.context)(ident=self.gen_ident())
        return super().begin_sequence(schema)

    def add_to_sequence(self, schema, sequence, idx, item):
        path = self.path_stack
        if isinstance(sequence, Seq) and len(path) == 2 and path[0] == 'data':
            if item is None:
                return sequence
            sequence[idx] = item
            return sequence
        return super().add_to_sequence(schema, sequence, idx, item)

    def assign(self, obj, key, val):
        path = self.path_stack
        if len(path) == 2 and path[0] == 'data' and isinstance(val, (dict, list)):
            val = DataLiteral(val)
        super().assign(obj, key, val)


DATA_LITERAL_SERIES = __name__ + '.DataLiteral'
register_id_series(DATA_LITERAL_SERIES)


class DataLiteral(rdflib.Literal):
    zodb_id_series = DATA_LITERAL_SERIES
