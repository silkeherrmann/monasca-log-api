# Copyright 2016 Hewlett Packard Enterprise Development Company, L.P.
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

import falcon
from monasca_common.kafka import producer
from monasca_common.rest import utils as rest_utils
from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils

from monasca_log_api.api import exceptions
from monasca_log_api.api import headers
from monasca_log_api.api import logs_v3_api
from monasca_log_api.v2.common import service
from monasca_log_api.v3.reference import helpers

LOG = log.getLogger(__name__)


class Logs(logs_v3_api.LogsV3Api):
    def __init__(self):
        super(Logs, self).__init__()
        self._service_config = cfg.CONF.service
        self._log_publisher_config = cfg.CONF.log_publisher
        self._kafka_producer = producer.KafkaProducer(
            self._log_publisher_config.kafka_url)

    def on_post(self, req, res):
        helpers.validate_json_content_type(req)
        service.Validations.validate_payload_size(req)
        cross_tenant_id = req.get_param('tenant_id')
        tenant_id = req.get_header(*headers.X_TENANT_ID)
        self._validate_cross_tenant_id(tenant_id, cross_tenant_id)
        request_body = helpers.read_json_msg_body(req)
        log_list = self._get_logs(request_body)
        envelopes = []
        for log_element in log_list:
            dimensions = self._get_dimensions(log_element)
            service.Validations.validate_dimensions(dimensions)
            log_message = self._get_log_message(log_element)
            envelope = self._create_log_envelope(tenant_id, cross_tenant_id,
                                                 self._service_config.region,
                                                 dimensions, log_message)
            service.Validations.validate_envelope_size(envelope)
            envelopes.append(envelope)

        self._send_logs(envelopes)
        res.status = falcon.HTTP_204

    def _validate_cross_tenant_id(self, tenant_id, cross_tenant_id):
        if not service.is_delegate(tenant_id):
            if cross_tenant_id:
                raise falcon.HTTPForbidden(
                    'Permission denied',
                    'Projects %s cannot POST cross tenant logs' % tenant_id
                )

    def _get_dimensions(self, log_element):
        '''Get the dimensions in the log element.'''
        if 'dimensions' not in log_element:
            raise exceptions.HTTPUnprocessableEntity(
                'Unprocessable Entity Dimensions not found')
        return log_element['dimensions']

    def _get_log_message(self, log_element):
        '''Get the message in the log element.'''
        if 'message' not in log_element:
            raise exceptions.HTTPUnprocessableEntity(
                'Unprocessable Entity Log message not found')
        return log_element['message']

    def _get_logs(self, request_body):
        '''Get the logs in the HTTP request body.'''
        if 'logs' not in request_body:
            raise exceptions.HTTPUnprocessableEntity(
                'Unprocessable Entity Logs not found')
        return request_body['logs']

    def _create_log_envelope(self, tenant_id, cross_tenant_id, region='',
                             dimensions={}, logs={}):
        '''Create a log envelope and return it as a json string.'''
        envelope = {
            'creation_time': timeutils.utcnow_ts(),
            'meta': {
                'tenantId': tenant_id if tenant_id else cross_tenant_id,
                'region': region
            },
            'dimensions': dimensions,
            'logs': logs
        }
        return rest_utils.as_json(envelope)

    def _send_logs(self, logs):
        '''Send the logs to Kafka.'''
        try:
            self._kafka_producer.publish(self._log_publisher_config.topics[0],
                                         logs,
                                         key=None)
        except Exception as ex:
            LOG.exception(ex)
            raise falcon.HTTPServiceUnavailable('Service unavailable',
                                                ex.message, 60)
