from .. import WormTracks

try:
    import numpy
    import pandas
    import tables
except ImportError:
    numpy = None
    pandas = None
    tables = None


class TierpsyWormTracks(WormTracks):
    '''
    A `WormTracks` that reads from a Tierpsy Tracker features file
    '''
    # recording61.4r_X1_features.hdf5
    def populate_from_features_file(self, features_file):
        pass
