'''
This example uses the WCON JSON-schema to build a DataSource type and then creates a new
DataSource with the values from an instance conforming to the schema
'''
from pkg_resources import resource_stream
import json
import importlib

from owmeta_core.context import ClassContext
from owmeta_core import BASE_CONTEXT
from owmeta_core.json_schema import DataSourceTypeCreator
from pow_zodb.ZODB import register_id_series
from rdflib.namespace import Namespace
from rdflib.term import Literal


BASE_SCHEMA_URL = 'http://schema.openworm.org/2020/07/sci/bio/movement'
BASE_DATA_URL = 'http://data.openworm.org/sci/bio/movement'


CONTEXT = ClassContext(imported=(BASE_CONTEXT,),
                      ident=BASE_SCHEMA_URL,
                      base_namespace=BASE_SCHEMA_URL + '#')


class MovementDataSourceTypeCreator(DataSourceTypeCreator):

    def __init__(self, name, schema, **kwargs):
        super().__init__(name,
                schema,
                module=__name__,
                context=CONTEXT,
                **kwargs)

    def create_type(self, path, schema):
        cdict = self.cdict.setdefault(path, {})
        cdict['base_namespace'] = Namespace(BASE_SCHEMA_URL + '/')
        cdict['base_data_namespace'] = Namespace(BASE_DATA_URL + '/')
        res = super().create_type(path, schema)
        mod = importlib.import_module(__name__)
        setattr(mod, res.__name__, res)
        res.register_on_module(mod)
        return res


_wcon_schema = resource_stream('owmeta_movement', 'wcon_schema_2017_06.json')
with _wcon_schema:
    _schema = json.load(_wcon_schema)

# If we later get another version of the schema or change how this data source is
# implemented, we can add on here. The dates are for the owmeta_movement schema version
# rather than the WCON schema version
WCON_SCHEMA_2020_07 = MovementDataSourceTypeCreator('MovementDataSource', _schema).annotate()

del _wcon_schema
del _schema


MovementDataSource = MovementDataSourceTypeCreator.retrieve_type(WCON_SCHEMA_2020_07)


DATA_LITERAL_SERIES = __name__ + '.DataLiteral'
register_id_series(DATA_LITERAL_SERIES)


class DataLiteral(Literal):
    zodb_id_series = DATA_LITERAL_SERIES
