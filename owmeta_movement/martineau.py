'''
For data from
Martineau, Celine N., & Nollen, Ellen A. A. (2018), mostly from Zenodo.
'''
from contextlib import contextmanager

from .zenodo import ZenodoFileDataSource
from .wcon import WCONDataSource


class MartineauWCONDataSource(WCONDataSource, ZenodoFileDataSource):

    @contextmanager
    def wcon_contents(self):
        raise NotImplementedError
