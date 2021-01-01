import argparse
import sys

from owmeta_core import BASE_CONTEXT
from owmeta_core.collections import Seq
from owmeta_core.command import OWM
from owmeta_core.context import Context
from owmeta_movement import DataRecord
from owmeta_movement.zenodo import ZenodoMovementDataSource
import matplotlib.pyplot as plt


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--context', help='Context from which the ZenodoMovementDataSource should be loaded')

    lookup_group = parser.add_mutually_exclusive_group(required=True)
    lookup_group.add_argument('--ident', help='Identifier for the data source to load')
    lookup_group.add_argument('--zenodo-id', help='Zenodo ID for the data source to load.'
            ' If more than one is available, then options will be shown and the command will exit',
            type=int)
    parser.add_argument('--record-index', help='The index of the record to plot. If not'
            ' provided, then all available records will be displayed', type=int)

    args = parser.parse_args()
    with OWM().connect() as conn:
        if args.context is None:
            context = args.context
        else:
            context = conn.owm.get_default_context()

        ctx = conn(Context)(context)
        ctx.add_import(BASE_CONTEXT)
        ds0 = ctx.stored(ZenodoMovementDataSource)(
                ident=args.ident,
                zenodo_id=args.zenodo_id)

        data_record = set(ds0.data.get()).pop()
        print('Data Record', data_record)
        if isinstance(data_record, Seq):
            stored_data_record = ctx.stored(data_record)
            if args.record_index is None:
                members = stored_data_record.rdfs_member()

                for record in members:
                    x = record.x()[0]
                    y = record.y()[0]
                    plt.plot(x, y)
            else:
                record = stored_data_record[args.record_index]
                if record is None:
                    print(f'No record at index {args.record_index}')
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


if __name__ == '__main__':
    sys.exit(main())
