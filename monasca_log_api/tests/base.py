# coding=utf-8
# Copyright 2015 kornicameister@gmail.com
# Copyright 2015-2017 FUJITSU LIMITED
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import codecs
import random
import string

import falcon
from falcon import testing
import mock
from oslo_config import fixture as oo_cfg
from oslo_context import fixture as oo_ctx
from oslotest import base as os_test
import six

from monasca_log_api.api.core import request
from monasca_log_api import conf


def mock_config(test):
    conf.register_opts()
    return test.useFixture(oo_cfg.Config(conf=conf.CONF))


def mock_context(test):
    return test.useFixture(oo_ctx.ClearRequestContext())


class MockedAPI(falcon.API):
    """MockedAPI

    Subclasses :py:class:`falcon.API` in order to overwrite
    request_type property with custom :py:class:`request.Request`

    """

    def __init__(self):
        super(MockedAPI, self).__init__(
            media_type=falcon.DEFAULT_MEDIA_TYPE,
            request_type=request.Request,
            response_type=falcon.Response,
            middleware=None,
            router=None
        )


def generate_unique_message(size):
    letters = string.ascii_letters

    def rand(amount, space=True):
        space = ' ' if space else ''
        return ''.join((random.choice(letters + space) for _ in range(amount)))

    return rand(size)


def _hex_to_unicode(hex_raw):
    hex_raw = six.b(hex_raw.replace(' ', ''))
    hex_str_raw = codecs.getdecoder('hex')(hex_raw)[0]
    hex_str = hex_str_raw.decode('utf-8', 'replace')
    return hex_str

# NOTE(trebskit) => http://www.cl.cam.ac.uk/~mgk25/ucs/examples/UTF-8-test.txt
UNICODE_MESSAGES = [
    # Unicode is evil...
    {'case': 'arabic', 'input': 'يونيكود هو الشر'},
    {'case': 'polish', 'input': 'Unicode to zło'},
    {'case': 'greek', 'input': 'Unicode είναι κακό'},
    {'case': 'portuguese', 'input': 'Unicode é malvado'},
    {'case': 'lao', 'input': 'unicode ເປັນຄວາມຊົ່ວຮ້າຍ'},
    {'case': 'german', 'input': 'Unicode ist böse'},
    {'case': 'japanese', 'input': 'ユニコードは悪です'},
    {'case': 'russian', 'input': 'Unicode - зло'},
    {'case': 'urdu', 'input': 'یونیسیڈ برائی ہے'},
    {'case': 'weird', 'input': '🆄🅽🅸🅲🅾🅳🅴 🅸🆂 🅴🆅🅸🅻...'},  # funky, huh ?
    # conditions from link above
    # 2.3  Other boundary conditions
    {'case': 'stress_2_3_1', 'input': _hex_to_unicode('ed 9f bf')},
    {'case': 'stress_2_3_2', 'input': _hex_to_unicode('ee 80 80')},
    {'case': 'stress_2_3_3', 'input': _hex_to_unicode('ef bf bd')},
    {'case': 'stress_2_3_4', 'input': _hex_to_unicode('f4 8f bf bf')},
    {'case': 'stress_2_3_5', 'input': _hex_to_unicode('f4 90 80 80')},
    # 3.5 Impossible byes
    {'case': 'stress_3_5_1', 'input': _hex_to_unicode('fe')},
    {'case': 'stress_3_5_2', 'input': _hex_to_unicode('ff')},
    {'case': 'stress_3_5_3', 'input': _hex_to_unicode('fe fe ff ff')},
    # 4.1 Examples of an overlong ASCII character
    {'case': 'stress_4_1_1', 'input': _hex_to_unicode('c0 af')},
    {'case': 'stress_4_1_2', 'input': _hex_to_unicode('e0 80 af')},
    {'case': 'stress_4_1_3', 'input': _hex_to_unicode('f0 80 80 af')},
    {'case': 'stress_4_1_4', 'input': _hex_to_unicode('f8 80 80 80 af')},
    {'case': 'stress_4_1_5', 'input': _hex_to_unicode('fc 80 80 80 80 af')},
    # 4.2 Maximum overlong sequences
    {'case': 'stress_4_2_1', 'input': _hex_to_unicode('c1 bf')},
    {'case': 'stress_4_2_2', 'input': _hex_to_unicode('e0 9f bf')},
    {'case': 'stress_4_2_3', 'input': _hex_to_unicode('f0 8f bf bf')},
    {'case': 'stress_4_2_4', 'input': _hex_to_unicode('f8 87 bf bf bf')},
    {'case': 'stress_4_2_5', 'input': _hex_to_unicode('fc 83 bf bf bf bf')},
    # 4.3  Overlong representation of the NUL character
    {'case': 'stress_4_3_1', 'input': _hex_to_unicode('c0 80')},
    {'case': 'stress_4_3_2', 'input': _hex_to_unicode('e0 80 80')},
    {'case': 'stress_4_3_3', 'input': _hex_to_unicode('f0 80 80 80')},
    {'case': 'stress_4_3_4', 'input': _hex_to_unicode('f8 80 80 80 80')},
    {'case': 'stress_4_3_5', 'input': _hex_to_unicode('fc 80 80 80 80 80')},
    # and some cheesy example from polish novel 'Pan Tadeusz'
    {'case': 'mr_t', 'input': 'Hajże na Soplicę!'},
    # it won't be complete without that one
    {'case': 'mr_b', 'input': 'Grzegorz Brzęczyszczykiewicz, '
                              'Chrząszczyżewoszyce, powiat Łękołody'},
    # great success, christmas time
    {'case': 'olaf', 'input': '☃'}
]


class DisableStatsdMixin(object):
    def setUp(self):
        super(DisableStatsdMixin, self).setUp()
        self.statsd_patch = mock.patch('monascastatsd.Connection')
        self.statsd_check = self.statsd_patch.start()


class BaseTestCase(DisableStatsdMixin, os_test.BaseTestCase):
    pass


class BaseApiTestCase(BaseTestCase, testing.TestBase):
    api_class = MockedAPI

    def before(self):
        self.conf = mock_config(self)
