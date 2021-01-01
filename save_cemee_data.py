import logging
import argparse

import transaction
from owmeta_core import BASE_CONTEXT
from owmeta_core.command import OWM
from owmeta_core.context import Context
from owmeta_movement import WCON_SCHEMA_2020_07
from owmeta_movement.zenodo import CeMEEDataSource
import requests
from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache

logging.basicConfig(level=logging.WARNING)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ident_group = parser.add_mutually_exclusive_group(required=True)
    ident_group.add_argument('--key', help='Key for the new data source')
    ident_group.add_argument('--ident', help='Identifier for the new data source')

    parser.add_argument('--zenodo-id', help='Zenodo ID', default=4074963)
    parser.add_argument('--zenodo-file-name',
            help='Name of the file from the CeMEE record',
            default='CeMEE_MWT_founders.tar.gz')
    parser.add_argument('--sample-zip-file-name',
            help='Name of the zip file *within* the archive named on Zenodo',
            default='AB1_20181119_104940.wcon.zip')

    http_cache_group = parser.add_mutually_exclusive_group(required=False)
    http_cache_group.add_argument('--http-cache-directory',
            help='HTTP cache directory',
            default='.http_cache')
    http_cache_group.add_argument('--no-http-cache', action='store_true', help='Do not do any HTTP caching')

    zenodo_cache_group = parser.add_mutually_exclusive_group(required=False)
    zenodo_cache_group.add_argument('--no-zenodo-cache', action='store_true',
            help='Do not cache files downloaded from Zenodo')
    zenodo_cache_group.add_argument('--zenodo-cache-directory',
            help='Directory where files from Zenodo are stored. The HTTP cache does not'
            ' necessarily provide headers for client-side caching',
            default='zenodo_cache')

    parser.add_argument('--context',
            help='Context where the DataSource will be saved. By default, will use the'
            ' project\'s default context')

    args = parser.parse_args()

    with OWM().connect() as conn:
        context = args.context
        if args.context is None:
            context = conn.owm.get_default_context()
        ctx = conn(Context)(context)
        ctx.add_import(BASE_CONTEXT)
        ds = ctx(CeMEEDataSource)(
                ident=args.ident,
                key=args.key,
                zenodo_id=args.zenodo_id,
                zenodo_file_name=args.zenodo_file_name,
                sample_zip_file_name=args.sample_zip_file_name)

        if args.no_http_cache:
            session = requests.Session()
        else:
            base_session = requests.Session()
            http_cache = FileCache(args.http_cache_directory)
            session = CacheControl(base_session, cache=http_cache)

        ds.populate_from_zenodo(
                WCON_SCHEMA_2020_07,
                session=session,
                cache_directory=args.zenodo_cache_directory)
        with transaction.manager:
            ctx.save()


if __name__ == '__main__':
    main()
