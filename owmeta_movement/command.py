import transaction
from owmeta_core.collections import Seq
from owmeta_core.command_util import SubCommand, GenericUserError, GeneratorWithData
from owmeta_core.utils import retrieve_provider
import matplotlib.pyplot as plt

from . import WormTracks, DataRecord
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

    def list_tracks(self):
        '''
        List WormTracks
        '''
        ctx = self._owm.default_context.stored
        tracks_q = ctx(WormTracks)()

        def format_id(r):
            return r.identifier

        def format_lab(r):
            md = r.metadata()
            return md.lab()

        return GeneratorWithData(tracks_q.load(),
                                 text_format=format_id,
                                 default_columns=('ID',),
                                 columns=(format_id,
                                          format_lab),
                                 header=('ID', 'Lab'))

    def plot(self, tracks, record_index=None):
        '''
        Do a plot of the given WormTracks

        Parameters
        ----------
        tracks : str
            ID of a WormTracks
        record_index : int
            Index of the record to plot. optional
        '''
        ctx = self._owm.default_context.stored
        data_record = set(ctx(WormTracks)(ident=tracks).data.get()).pop()
        print('Data Record', data_record)
        if isinstance(data_record, Seq):
            stored_data_record = ctx.stored(data_record)
            if record_index is None:
                members = stored_data_record.rdfs_member()

                for record in members:
                    x = record.x()[0]
                    y = record.y()[0]
                    plt.plot(x, y)
            else:
                record = stored_data_record[record_index]
                if record is None:
                    self._owm.message(f'No record at index {record_index}')
                    return 1
                x = record.x()[0]
                y = record.y()[0]
                plt.plot(x, y)

        elif isinstance(data_record, DataRecord):
            x = record.x()[0]
            y = record.y()[0]
            plt.plot(x, y)
        else:
            print(f'Cannot plot record {data_record}')
            return 1

        plt.show()


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
