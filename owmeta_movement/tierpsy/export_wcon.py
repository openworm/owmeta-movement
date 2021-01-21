# -*- coding: utf-8 -*-
# MIT License

# Copyright (c) 2017 Medical Research Council

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
'''
Utilities for reading movement data from Tierpsy HDF5 files

Created on Mon Aug 15 20:55:19 2016

@author: ajaver
'''

from collections import OrderedDict
import json

import numpy as np
import pandas as pd
import tables

from .obtain_features_helper import WormStats
from .param_readers import read_unit_conversions, read_ventral_side, read_fps


wcon_metadata_fields = ['id', 'lab', 'who', 'timestamp', 'temperature', 'humidity', 'arena',
                        'food', 'media', 'sex', 'stage', 'age', 'strain', 'protocol', 'interpolate', 'software']


def wcon_reformat_metadata(metadata_dict):
    wcon_metadata = OrderedDict()
    for field in wcon_metadata_fields:
        if field in metadata_dict:
            wcon_metadata[field] = metadata_dict[field]

    wcon_metadata['@OMG'] = OrderedDict()
    for field in metadata_dict:
        if field not in wcon_metadata_fields:
            wcon_metadata['@OMG'][field] = metadata_dict[field]

    if '@OMG' in metadata_dict:
        for field in metadata_dict['@OMG']:
            wcon_metadata['@OMG'][field] = metadata_dict['@OMG'][field]

    return wcon_metadata


def readMetaData(fname, provenance_step='FEAT_CREATE'):
    def _order_metadata(metadata_dict):
        ordered_fields = ['strain', 'timestamp', 'gene', 'chromosome', 'allele',
                          'strain_description', 'sex', 'stage', 'ventral_side', 'media', 'arena', 'food',
                          'habituation', 'who', 'protocol', 'lab', 'software']

        extra_fields = metadata_dict.keys() - set(ordered_fields)
        ordered_fields += sorted(extra_fields)

        ordered_metadata = OrderedDict()
        for field in ordered_fields:
            if field in metadata_dict:
                ordered_metadata[field] = metadata_dict[field]
        return ordered_metadata

    with tables.File(fname, 'r') as fid:
        if '/experiment_info' not in fid:
            experiment_info = {}
        else:
            experiment_info = fid.get_node('/experiment_info').read()
            experiment_info = json.loads(experiment_info.decode('utf-8'))

        provenance_tracking = fid.get_node('/provenance_tracking/' + provenance_step).read()
        provenance_tracking = json.loads(provenance_tracking.decode('utf-8'))

        if 'commit_hash' in provenance_tracking:
            # old name
            pkgs_versions = provenance_tracking['commit_hash']
        else:
            pkgs_versions = provenance_tracking['pkgs_versions']

        if 'tierpsy' in pkgs_versions:
            tierpsy_version = pkgs_versions['tierpsy']
        else:
            tierpsy_version = pkgs_versions['MWTracker']

        MWTracker_ver = {"name": "tierpsy (https://github.com/ver228/tierpsy-tracker)",
                         "version": tierpsy_version,
                         "featureID": "@OMG"}

        experiment_info["software"] = MWTracker_ver

    return _order_metadata(experiment_info)


def __reformatForJson(A):
    if isinstance(A, (int, float)):
        return A

    good = ~np.isnan(A) & (A != 0)
    dd = A[good]
    if dd.size > 0:
        dd = np.abs(np.floor(np.log10(np.abs(dd))) - 2)
        precision = max(2, int(np.min(dd)))
        A = np.round(A.astype(np.float64), precision)
    A = np.where(np.isnan(A), None, A)

    # wcon specification require to return a single number if it is only one element list
    if A.size == 1:
        return A[0]
    else:
        return A.tolist()


def __addOMGFeat(fid, worm_feat_time, worm_id):
    worm_features = OrderedDict()
    # add time series features
    for col_name, col_dat in worm_feat_time.iteritems():
        if col_name not in ['worm_index', 'timestamp']:
            worm_features[col_name] = col_dat.values

    worm_path = '/features_events/worm_%i' % worm_id
    worm_node = fid.get_node(worm_path)
    # add event features
    for feature_name in worm_node._v_children:
        feature_path = worm_path + '/' + feature_name
        worm_features[feature_name] = fid.get_node(feature_path)[:]

    return worm_features


def _get_ventral_side(features_file):
    ventral_side = read_ventral_side(features_file)
    if not ventral_side or ventral_side == 'unknown':
        ventral_type = '?'
    else:
        # we will merge the ventral and dorsal contours so the ventral contour is clockwise
        ventral_type = 'CW'
    return ventral_type


def readData(features_file, READ_FEATURES=False, IS_FOR_WCON=True):
    '''
    Read 'data' records from the features file, one per worm index

    Parameters
    ----------
    features_file : ...
        HDF5 features file file from which data is to be read
    READ_FEATURES : bool, optional
        If `True`, add custom features to each record
    IS_FOR_WCON : bool, optional
        If `True`, then the records are formatted for WCON JSON output. This adjusts
        the types of some feature values and sets the lab prefix for features ("@OMG")

    Yields
    ------
    dict
        Data records
    '''
    if IS_FOR_WCON:
        lab_prefix = '@OMG '
    else:
        lab_prefix = ''

    with pd.HDFStore(features_file, 'r') as fid:
        if '/features_timeseries' not in fid:
            return {}  # empty file nothing to do here

        features_timeseries = fid['/features_timeseries']
        feat_time_group_by_worm = features_timeseries.groupby('worm_index')

    ventral_side = _get_ventral_side(features_file)

    with tables.File(features_file, 'r') as fid:
        # fps used to adjust timestamp to real time
        fps = read_fps(features_file)

        # get pointers to some useful data
        skeletons = fid.get_node('/coordinates/skeletons')
        dorsal_contours = fid.get_node('/coordinates/dorsal_contours')
        ventral_contours = fid.get_node('/coordinates/ventral_contours')

        # let's append the data of each individual worm as a element in a list

        # group by iterator will return sorted worm indexes
        for worm_id, worm_feat_time in feat_time_group_by_worm:

            worm_id = int(worm_id)
            # read worm skeletons data
            worm_skel = skeletons[worm_feat_time.index]
            worm_dor_cnt = dorsal_contours[worm_feat_time.index]
            worm_ven_cnt = ventral_contours[worm_feat_time.index]

            # start ordered dictionary with the basic features
            worm_basic = OrderedDict()
            worm_basic['id'] = str(worm_id)
            worm_basic['head'] = 'L'
            worm_basic['ventral'] = ventral_side
            worm_basic['ptail'] = worm_ven_cnt.shape[1] - 1  # index starting with 0

            worm_basic['t'] = worm_feat_time['timestamp'].values / fps  # convert from frames to seconds
            worm_basic['x'] = worm_skel[:, :, 0]
            worm_basic['y'] = worm_skel[:, :, 1]

            contour = np.hstack((worm_ven_cnt, worm_dor_cnt[:, ::-1, :]))
            worm_basic['px'] = contour[:, :, 0]
            worm_basic['py'] = contour[:, :, 1]

            if READ_FEATURES:
                worm_features = __addOMGFeat(fid, worm_feat_time, worm_id)
                for feat in worm_features:
                    worm_basic[lab_prefix + feat] = worm_features[feat]

            if IS_FOR_WCON:
                for x in worm_basic:
                    if x not in ['id', 'head', 'ventral', 'ptail']:
                        worm_basic[x] = __reformatForJson(worm_basic[x])

            # append features
            yield worm_basic


def readUnits(features_file, READ_FEATURES=False):
    '''
    Read in the units for the corresponding data records recoverable from the features
    file

    Parameters
    ----------
    features_file : ...
        HDF5 features file file from which units are to be read
    READ_FEATURES : bool, optional
        If `True`, add units for custom features to each record

    Returns
    -------
    dict
        The units for each field
    '''
    fps_out, microns_per_pixel_out, _ = read_unit_conversions(features_file)
    xy_units = microns_per_pixel_out[1]
    time_units = fps_out[2]

    units = OrderedDict()
    units["size"] = "mm"  # size of the plate
    units['t'] = time_units  # frames or seconds

    for field in ['x', 'y', 'px', 'py']:
        units[field] = xy_units  # (pixels or micrometers)

    if READ_FEATURES:
        # TODO how to change microns to pixels when required
        ws = WormStats()
        for field, unit in ws.features_info['units'].iteritems():
            units['@OMG ' + field] = unit

    return units
