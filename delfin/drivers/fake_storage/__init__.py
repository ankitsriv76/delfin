# Copyright 2020 The SODA Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
import datetime
import decorator
import math
import six
import time
from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils

from delfin import exception
from delfin.common import constants
from delfin.drivers import driver

CONF = cfg.CONF

fake_opts = [
    cfg.StrOpt('fake_pool_range',
               default='1-100',
               help='The range of pool number for one device.'),
    cfg.StrOpt('fake_volume_range',
               default='1-2000',
               help='The range of volume number for one device.'),
    cfg.StrOpt('fake_api_time_range',
               default='0.1-0.5',
               help='The range of time cost for each API.'),
    cfg.StrOpt('fake_page_query_limit',
               default='500',
               help='The limitation of volumes for each query.'),
]

CONF.register_opts(fake_opts, "fake_driver")

LOG = log.getLogger(__name__)

MIN_WAIT, MAX_WAIT = 0.1, 0.5
MIN_POOL, MAX_POOL = 1, 100
MIN_VOLUME, MAX_VOLUME = 1, 2000
MIN_CONTROLLERS, MAX_CONTROLLERS = 1, 5
PAGE_LIMIT = 500
MIN_STORAGE, MAX_STORAGE = 1, 10
MIN_PERF_VALUES, MAX_PERF_VALUES = 1, 4


def get_range_val(range_str, t):
    try:
        rng = range_str.split('-')
        if len(rng) != 2:
            raise exception.InvalidInput
        min_val = t(rng[0])
        max_val = t(rng[1])
        return min_val, max_val
    except Exception:
        LOG.error("Invalid range: {0}".format(range_str))
        raise exception.InvalidInput


def wait_random(low, high):
    @decorator.decorator
    def _wait(f, *a, **k):
        rd = random.randint(0, 100)
        secs = low + (high - low) * rd / 100
        time.sleep(secs)
        return f(*a, **k)

    return _wait


class FakeStorageDriver(driver.StorageDriver):
    """FakeStorageDriver shows how to implement the StorageDriver,
    it also plays a role as faker to fake data for being tested by clients.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        global MIN_WAIT, MAX_WAIT, MIN_POOL, MAX_POOL, MIN_VOLUME, MAX_VOLUME
        global PAGE_LIMIT
        MIN_WAIT, MAX_WAIT = get_range_val(
            CONF.fake_driver.fake_api_time_range, float)
        MIN_POOL, MAX_POOL = get_range_val(
            CONF.fake_driver.fake_pool_range, int)
        MIN_VOLUME, MAX_VOLUME = get_range_val(
            CONF.fake_driver.fake_volume_range, int)
        PAGE_LIMIT = int(CONF.fake_driver.fake_page_query_limit)

    def _get_random_capacity(self):
        total = random.randint(1000, 2000)
        used = int(random.randint(0, 100) * total / 100)
        free = total - used
        return total, used, free

    def reset_connection(self, context, **kwargs):
        pass

    @wait_random(MIN_WAIT, MAX_WAIT)
    def get_storage(self, context):
        # Do something here
        sn = six.text_type(uuidutils.generate_uuid())
        total, used, free = self._get_random_capacity()
        raw = random.randint(2000, 3000)
        subscribed = random.randint(3000, 4000)
        return {
            'name': 'fake_driver',
            'description': 'fake driver.',
            'vendor': 'fake_vendor',
            'model': 'fake_model',
            'status': 'normal',
            'serial_number': sn,
            'firmware_version': '1.0.0',
            'location': 'HK',
            'total_capacity': total,
            'used_capacity': used,
            'free_capacity': free,
            'raw_capacity': raw,
            'subscribed_capacity': subscribed
        }

    @wait_random(MIN_WAIT, MAX_WAIT)
    def list_storage_pools(self, ctx):
        rd_pools_count = random.randint(MIN_POOL, MAX_POOL)
        LOG.info("###########fake_pools number for %s: %d" % (self.storage_id,
                                                              rd_pools_count))
        pool_list = []
        for idx in range(rd_pools_count):
            total, used, free = self._get_random_capacity()
            p = {
                "name": "fake_pool_" + str(idx),
                "storage_id": self.storage_id,
                "native_storage_pool_id": "fake_original_id_" + str(idx),
                "description": "Fake Pool",
                "status": "normal",
                "total_capacity": total,
                "used_capacity": used,
                "free_capacity": free,
            }
            pool_list.append(p)
        return pool_list

    def list_volumes(self, ctx):
        # Get a random number as the volume count.
        rd_volumes_count = random.randint(MIN_VOLUME, MAX_VOLUME)
        LOG.info("###########fake_volumes number for %s: %d" % (
            self.storage_id, rd_volumes_count))
        loops = math.ceil(rd_volumes_count / PAGE_LIMIT)
        volume_list = []
        for idx in range(loops):
            start = idx * PAGE_LIMIT
            end = (idx + 1) * PAGE_LIMIT
            if idx == (loops - 1):
                end = rd_volumes_count
            vs = self._get_volume_range(start, end)
            volume_list = volume_list + vs
        return volume_list

    def list_controllers(self, ctx):
        rd_controllers_count = random.randint(MIN_CONTROLLERS, MAX_CONTROLLERS)
        LOG.info("###########fake_controllers for %s: %d" %
                 (self.storage_id, rd_controllers_count))
        ctrl_list = []
        for idx in range(rd_controllers_count):
            total, used, free = self._get_random_capacity()
            cpu = ["Intel Xenon", "Intel Core ix", "ARM"]
            sts = list(constants.ControllerStatus.ALL)
            sts_len = len(constants.ControllerStatus.ALL) - 1
            c = {
                "name": "fake_ctrl_" + str(idx),
                "storage_id": self.storage_id,
                "native_controller_id": "fake_original_id_" + str(idx),
                "location": "loc_" + str(random.randint(0, 99)),
                "status": sts[random.randint(0, sts_len)],
                "memory_size": total,
                "cpu_info": cpu[random.randint(0, 2)],
                "soft_version": "ver_" + str(random.randint(0, 999)),
            }
            ctrl_list.append(c)
        return ctrl_list

    def add_trap_config(self, context, trap_config):
        pass

    def remove_trap_config(self, context, trap_config):
        pass

    def parse_alert(self, context, alert):
        pass

    def clear_alert(self, context, alert):
        pass

    def list_alerts(self, context, query_para=None):
        pass

    @wait_random(MIN_WAIT, MAX_WAIT)
    def _get_volume_range(self, start, end):
        volume_list = []

        for i in range(start, end):
            total, used, free = self._get_random_capacity()
            v = {
                "name": "fake_vol_" + str(i),
                "storage_id": self.storage_id,
                "description": "Fake Volume",
                "status": "normal",
                "native_volume_id": "fake_original_id_" + str(i),
                "wwn": "fake_wwn_" + str(i),
                "total_capacity": total,
                "used_capacity": used,
                "free_capacity": free,
            }
            volume_list.append(v)
        return volume_list

    def _get_random_performance(self):
        def get_random_timestamp_value():
            rtv = {}
            for i in range(MIN_PERF_VALUES, MAX_PERF_VALUES):
                timestamp = int(float(datetime.datetime.now().timestamp()
                                      ) * 1000)
                rtv[timestamp] = random.uniform(1, 100)
            return rtv

        # The sample performance_params after filling looks like,
        # performance_params = {timestamp1: value1, timestamp2: value2}
        performance_params = {}
        for key in constants.DELFIN_ARRAY_METRICS:
            performance_params[key] = get_random_timestamp_value()
        return performance_params

    @wait_random(MIN_WAIT, MAX_WAIT)
    def collect_array_metrics(self, ctx, storage_id, interval, is_history):
        rd_array_count = random.randint(MIN_STORAGE, MAX_STORAGE)
        LOG.info("Fake_array_metrics number for %s: %d" % (
            storage_id, rd_array_count))
        array_metrics = []
        labels = {'storage_id': storage_id, 'resource_type': 'array'}
        fake_metrics = self._get_random_performance()

        for _ in range(rd_array_count):
            for key in constants.DELFIN_ARRAY_METRICS:
                m = constants.metric_struct(name=key, labels=labels,
                                            values=fake_metrics[key])
                array_metrics.append(m)

        return array_metrics
