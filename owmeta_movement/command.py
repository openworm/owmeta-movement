import transaction
from owmeta_core.command_util import SubCommand, GenericUserError
from owmeta_core.utils import retrieve_provider

from .zenodo import list_record_files
from .cemee import CeMEEWCONDataSource, CeMEEDataTranslator


class CeMEECommand:
    '''
    Commands for doing stuff with CeMEE data
    '''

    def __init__(self, parent):
        self._parent = parent
        self._owm = parent._parent

    def save(self, zenodo_id, zenodo_file_name, sample_zip_file_name, ident=None, key=None):
        '''
        Save a `CeMEEWCONDataSource` for a given zenodo_id.

        At either `ident` or `key` must be provided.

        Parameters
        ----------
        zenodo_id : int
            The Zenodo record ID to make a DataSource for
        zenodo_file_name : str
            File name in the Zenodo record
        sample_zip_file_name : str
            File name of a ZIP file within the Zenodo file
        ident : str
            The identifier for the new DataSource
        key : str
            Key for DataSource identifiers
        '''

        if not key and not ident:
            raise GenericUserError('Either ident or key must be provided')
        ctx = self._owm.default_context
        ctx.add_import(CeMEEWCONDataSource.definition_context)
        with transaction.manager:
            ctx(CeMEEWCONDataSource)(
                    ident=ident,
                    key=key,
                    zenodo_id=zenodo_id,
                    zenodo_file_name=zenodo_file_name,
                    sample_zip_file_name=sample_zip_file_name)
            ctx.save()

    def translate(self, data_source):
        '''
        Translate a CeMEEWCONDataSource into a MovementDataSource

        Parameters
        ----------
        data_source : str
            The identifier for the data source
        '''
        dt = CeMEEDataTranslator()
        self._owm.translate(dt, data_sources=(data_source,))


class MovementCommand:
    '''
    Commands for C. elegans movement data
    '''

    cemee = SubCommand(CeMEECommand)

    def __init__(self, parent):
        self._parent = parent
        self._owm = parent


class ZenodoCommand:
    def __init__(self, parent):
        self._parent = parent

    def list_files(self, zenodo_id, zenodo_base_url=None, session_provider=None):
        '''
        List files in a Zenodo record

        Parameters
        ----------
        zenodo_id : int
            The Zenodo record ID
        zenodo_base_url : str
            The base URL for zenodo. optional: Uses the well-known Zenodo URL if not provided
        session_provider : str
            Path to a callable that provides a `requests.Session`. Provides session to use
            for requests to Zenodo. The format is similar to that for setuptools entry
            points: ``path.to.module:path.to.provider.callable``.  Notably, there's no
            name and "extras" are not supported. optional.
        '''
        if session_provider is not None:
            session = retrieve_provider(session_provider)()
        else:
            session = None
        return list_record_files(zenodo_id, zenodo_base_url=zenodo_base_url,
                session=session)
