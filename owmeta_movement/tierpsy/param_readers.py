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
import json
import os

import numpy as np
import tables


VALID_FIELDS = ['/mask', '/trajectories_data', '/features_timeseries']


def read_unit_conversions(fname, dflt=1):
    reader = AttrReader(fname, dflt)
    fps_out = reader.get_fps()

    microns_per_pixel_out = reader.get_microns_per_pixel()
    is_light_background = reader._read_attr('is_light_background', 1)

    return fps_out, microns_per_pixel_out, is_light_background


def read_ventral_side(fname):
    # I am giving priority to a contour stored in experiments_info, rather than one read by the json file.
    # currently i am only using the experiments_info in the re-analysis of the old schafer database
    reader = AttrReader(fname)
    ventral_side = reader.ventral_side
    return ventral_side


def read_fps(fname, dflt=1):
    reader = AttrReader(fname, dflt)
    return reader.fps


class AttrReader():
    def __init__(self, file_name, dflt=1):
        self.file_name = file_name
        self.dflt = dflt
        self.field = self._find_field()

    def _find_field(self):
        if os.path.exists(self.file_name):
            with tables.File(self.file_name, 'r') as fid:
                for field in VALID_FIELDS:
                    if field in fid:
                        return field
        #raise KeyError("Not valid field {} found in {}".format(VALID_FIELDS, self.file_name))
        return ''

    def _read_attr(self, attr_name, dflt=None):

        if dflt is None:
            dflt = self.dflt

        attr = dflt
        if self.field:
            with tables.File(self.file_name, 'r') as fid:
                node = fid.get_node(self.field)

                if attr_name in node._v_attrs:
                    attr = node._v_attrs[attr_name]
        return attr

    def get_fps(self):
        expected_fps = self._read_attr('expected_fps', dflt=1)
        try:
            fps, time_units = fps_from_timestamp(self.file_name)

        except (tables.exceptions.NoSuchNodeError, IOError, ValueError, KeyError):
            fps = self._read_attr('fps', dflt=-1)
            if fps < 0:
                # read the user defined timestamp
                fps = expected_fps

            time_units = self._read_attr('time_units', dflt=None)
            if not isinstance(time_units, str):
                if fps == 1:
                    time_units = 'frames'
                else:
                    time_units = 'seconds'

        self._fps = float(fps)
        self._expected_fps = float(expected_fps)
        self._time_units = time_units

        return self._fps, self._expected_fps, self._time_units

    @property
    def fps(self):
        try:
            return self._fps
        except BaseException:
            self.get_fps()
            return self._fps

    @property
    def time_units(self):
        try:
            return self._time_units
        except BaseException:
            self.get_fps()
            return self._time_units

    def get_microns_per_pixel(self):
        try:
            microns_per_pixel, xy_units = single_db_microns_per_pixel(self.file_name)
        except (tables.exceptions.NoSuchNodeError, IOError, ValueError, KeyError):
            microns_per_pixel = self._read_attr('microns_per_pixel', dflt=1)
            xy_units = self._read_attr('xy_units', dflt=None)
            if xy_units is None:
                if microns_per_pixel == 1:
                    xy_units = 'pixels'
                else:
                    xy_units = 'micrometers'

        self._microns_per_pixel = float(microns_per_pixel)
        self._xy_units = xy_units
        return self._microns_per_pixel, self._xy_units

    @property
    def microns_per_pixel(self):
        try:
            return self._microns_per_pixel
        except BaseException:
            self.get_microns_per_pixel()
            return self._microns_per_pixel

    @property
    def xy_units(self):
        try:
            return self._xy_units
        except BaseException:
            self.get_microns_per_pixel()
            return self._xy_units

    @property
    def ventral_side(self):
        try:
            return self._ventral_side
        except BaseException:
            try:
                ventral_side = single_db_ventral_side(self.file_name)
            except BaseException:
                ventral_side = self._read_attr('ventral_side', dflt="")

            self._ventral_side = ventral_side
            return self._ventral_side


def fps_from_timestamp(file_name):
    # try to calculate the frames per second from the timestamp
    with tables.File(file_name, 'r') as fid:
        timestamp_time = fid.get_node('/timestamp/time')[:]
        if np.all(np.isnan(timestamp_time)):
            raise ValueError

        delT = np.nanmedian(np.diff(timestamp_time))
        if delT == 0:
            raise ValueError
        fps = 1 / delT

        if np.isnan(fps) or fps < 1:
            raise ValueError

        time_units = 'seconds'

    return fps, time_units


def single_db_ventral_side(file_name):
    # this for the shaffer's lab old database
    with tables.File(file_name, 'r') as fid:
        exp_info_b = fid.get_node('/experiment_info').read()
        exp_info = json.loads(exp_info_b.decode("utf-8"))
        ventral_side = exp_info['ventral_side']
    return ventral_side


def single_db_microns_per_pixel(file_name):
    # this is used in the single worm case, but it would be deprecated. I want to use this
    # argument when I read the data from original additional files
    with tables.File(file_name, 'r') as fid:
        microns_per_pixel_scale = fid.get_node('/stage_movement')._v_attrs['microns_per_pixel_scale']
        if microns_per_pixel_scale.size == 2:
            assert np.abs(
                microns_per_pixel_scale[0]) == np.abs(
                microns_per_pixel_scale[1])
            microns_per_pixel = np.abs(microns_per_pixel_scale[0])
    xy_units = 'micrometers'

    return microns_per_pixel, xy_units
