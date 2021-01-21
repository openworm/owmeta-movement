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
from collections import OrderedDict

import numpy as np
import pandas as pd
from pkg_resources import Requirement, resource_stream


class WormStats:
    def __init__(self):
        '''get the info for each feature chategory'''

        self.extra_fields = ['worm_index', 'n_frames', 'n_valid_skel', 'first_frame']
        feat_csv = resource_stream(Requirement.parse('owmeta_movement'), 'feature_names.csv')
        with feat_csv as feats:
            self.features_info = pd.read_csv(feats, index_col=0)
        self.builtFeatAvgNames()  # create self.feat_avg_names

        # get files that would be used in the construction of objects
        self.feat_avg_dtype = [(x, np.float32) for x in self.feat_avg_names]
        self.feat_timeseries = list(
            self.features_info[
                self.features_info['is_time_series'] == 1].index.values)

        extra_fields = ['worm_index', 'timestamp', 'skeleton_id', 'motion_modes']
        timeseries_fields = extra_fields + self.feat_timeseries
        self.feat_timeseries_dtype = [(x, np.float32) for x in timeseries_fields]

        self.feat_events = list(
            self.features_info[
                self.features_info['is_time_series'] == 0].index.values)

    def builtFeatAvgNames(self):
        feat_avg_names = self.extra_fields[:]
        for feat_name, feat_info in self.features_info.iterrows():

            motion_types = ['']
            if feat_info['is_time_series']:
                motion_types += ['_forward', '_paused', '_backward']

            for mtype in motion_types:
                sub_name = feat_name + mtype
                feat_avg_names.append(sub_name)
                if feat_info['is_signed']:
                    for atype in ['_abs', '_neg', '_pos']:
                        feat_avg_names.append(sub_name + atype)

        self.feat_avg_names = feat_avg_names

    def getFieldData(worm_features, name):
        data = worm_features
        for field in name.split('.'):
            data = getattr(data, field)
        return data

    def getWormStats(self, worm_features, stat_func=np.mean):
        ''' Calculate the statistics of an object worm features, subdividing data
            into Backward/Forward/Paused and/or Positive/Negative/Absolute, when appropiated.
            The default is to calculate the mean value, but this can be changed
            using stat_func.

            Return the feature list as an ordered dictionary.
        '''

        if isinstance(worm_features, (dict, pd.DataFrame)):
            def read_feat(feat_name):
                if feat_name in worm_features:
                    return worm_features[feat_name]
                else:
                    return None
            motion_mode = read_feat('motion_modes')
        else:

            def read_feat(feat_name):
                feat_obj = self.features_info.loc[feat_name, 'feat_name_obj']
                if feat_obj in worm_features._features:
                    return worm_features._features[feat_obj].value
                else:
                    return None
            motion_mode = worm_features._features['locomotion.motion_mode'].value

        # return data as a numpy recarray
        feat_stats = np.full(1, np.nan, dtype=self.feat_avg_dtype)

        for feat_name, feat_props in self.features_info.iterrows():
            tmp_data = read_feat(feat_name)
            if tmp_data is None:
                feat_stats[feat_name] = np.nan

            elif isinstance(tmp_data, (int, float)):
                feat_stats[feat_name] = tmp_data

            else:
                feat_avg = self._featureStat(
                    stat_func,
                    tmp_data,
                    feat_name,
                    feat_props['is_signed'],
                    feat_props['is_time_series'],
                    motion_mode)
                for feat_avg_name in feat_avg:
                    feat_stats[feat_avg_name] = feat_avg[feat_avg_name]

        return feat_stats

    @staticmethod
    def _featureStat(
            stat_func,
            data,
            name,
            is_signed,
            is_time_series,
            motion_mode=np.zeros(0)):
        # I prefer to keep this function quite independend and pass the stats and moition_mode argument
        # rather than save those values in the class
        if data is None:
            data = np.zeros(0)

        # filter nan data
        valid = ~np.isnan(data)
        data = data[valid]

        motion_types = OrderedDict()
        motion_types['all'] = np.nan
        if is_time_series:
            # if the the feature is motion type we can subdivide in Forward,
            # Paused or Backward motion
            motion_mode = motion_mode[valid]
            assert motion_mode.size == data.size

            motion_types['forward'] = motion_mode == 1
            motion_types['paused'] = motion_mode == 0
            motion_types['backward'] = motion_mode == -1

        stats = OrderedDict()
        for key in motion_types:

            if key == 'all':
                sub_name = name
                valid_data = data
            else:
                sub_name = name + '_' + key
                # filter by an specific motion type
                valid_data = data[motion_types[key]]

            assert not np.any(np.isnan(valid_data))

            stats[sub_name] = stat_func(valid_data)
            if is_signed:
                # if the feature is signed we can subdivide in positive,
                # negative and absolute
                stats[sub_name + '_abs'] = stat_func(np.abs(valid_data))

                neg_valid = (valid_data < 0)
                stats[sub_name + '_neg'] = stat_func(valid_data[neg_valid])

                pos_valid = (valid_data > 0)
                stats[sub_name + '_pos'] = stat_func(valid_data[pos_valid])
        return stats
