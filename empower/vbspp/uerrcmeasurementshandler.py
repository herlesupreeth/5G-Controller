#!/usr/bin/env python3
#
# Copyright (c) 2015, Roberto Riggio, Supreeth Herle
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the CREATE-NET nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY CREATE-NET ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL CREATE-NET BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""UE RRC Measurements Handler."""

import tornado.web
import tornado.httpserver
import uuid

from empower.datatypes.etheraddress import EtherAddress
from empower.main import RUNTIME
from empower.vbspp import REPORT_INTERVAL
from empower.restserver.apihandlers import EmpowerAPIHandlerAdminUsers

import empower.logger
LOG = empower.logger.get_logger()


class UERRCMeasurementsHandler(EmpowerAPIHandlerAdminUsers):
    """UERRCMeasurements handler. Used to view and manipulate UE RRC Measurements in tenants."""

    HANDLERS = [r"/api/v1/tenants/([a-zA-Z0-9-]*)/vbsps/([a-zA-Z0-9:]*)/ues/([a-zA-Z0-9]*)/ue_rrc_measurements/?"]

    def post(self, *args, **kwargs):
        """ Change the RRC Measurements configuration for a specified UE in a VBSP.

        Args:
            tenant_id: the tenant identifier
            vbsp_id: the vbsp identifier
            rnti: the radio network temporary identifier

        Example URLs:
            GET /api/v1/tenants/daa2b515-8aed-4e6b-b171-2ff4dd12b768/vbsps/11:22:33:44:55:66/ues/bb96/ue_rrc_measurements

        data: '{
                    "version" : "1.0",
                    "rrc_measurements_request": {
                        "reportInterval": "10240ms", // ("480ms", "640ms", "1024ms", "2048ms", "5120ms", "10240ms", "1min", "6min", "12min", "30min", "60min")
                        "reporting_carrier_frequency": 1850, // (Earfcn), make sure this band is supported by the UE
                    }
               }'
        """

        try:

            if len(args) < 3 or len(args) > 3:
                raise ValueError("Invalid URL")

            request = tornado.escape.json_decode(self.request.body)

            if "version" not in request:
                raise ValueError("missing version element")

            if "rrc_measurements_request" not in request:
                raise ValueError("missing rrc_measurements_request element")

            if "reportInterval" not in request["rrc_measurements_request"] or "reporting_carrier_frequency" not in request["rrc_measurements_request"]:
                raise ValueError("missing request parameters element")

            if "reportInterval" in request["rrc_measurements_request"] and request["rrc_measurements_request"]["reportInterval"] not in REPORT_INTERVAL:
                raise ValueError("Incorrect reportInterval parameters")

            if "reporting_carrier_frequency" in request["rrc_measurements_request"]:
                # crude check for integer value given for EARFCN
                int(request["rrc_measurements_request"]["reporting_carrier_frequency"])

            vbsp = None
            tenant_id = uuid.UUID(args[0])
            tenant = RUNTIME.tenants[tenant_id]
            vbsp = tenant.vbsps[EtherAddress(args[1])]
            vbsp_connection = vbsp.connection
            ue_rnti = int(args[2])

            if len(vbsp.ues) == 0:
                raise ValueError("No UEs are registered to vbsp")

            if ue_rnti not in vbsp.ues:
                raise ValueError("Incorrect rnti of UE")

            # ue_rnti is used a xid (transaction id)
            # could you used in future to check whether the configuration was taken into effect or not
            vbsp_connection.send_rrc_meas_reconfig_request(request, ue_rnti)

        except KeyError as ex:
            self.send_error(404, message=ex)
        except ValueError as ex:
            self.send_error(400, message=ex)
        
        self.set_status(200, None)

    def get(self, *args, **kwargs):
        """ Get RRC Measurements for a specified UE in a VBSP.

        Args:
            tenant_id: the tenant identifier
            vbsp_id: the vbsp identifier
            rnti: the radio network temporary identifier

        Example URLs:
            GET /api/v1/tenants/daa2b515-8aed-4e6b-b171-2ff4dd12b768/vbsps/11:22:33:44:55:66/ues/bb96/ue_rrc_measurements
        """

        try:

            if len(args) < 3 or len(args) > 3:
                raise ValueError("Invalid URL")

            vbsp = None
            tenant_id = uuid.UUID(args[0])
            tenant = RUNTIME.tenants[tenant_id]
            vbsp = tenant.vbsps[EtherAddress(args[1])]
            ue_rnti = int(args[2])

            if len(vbsp.ues) == 0:
                raise ValueError("No UEs are registered to vbsp")

            if ue_rnti not in vbsp.ues:
                raise ValueError("Incorrect rnti of UE")

            ue = vbsp.ues[ue_rnti]
            self.write_as_json({
                'primary_cell_rsrp': ue.PCell_rsrp,
                'primary_cell_rsrq': ue.PCell_rsrq,
                'rrc_measurements': ue.rrc_measurements
            })
            self.set_status(200, None)

        except ValueError as ex:
            self.send_error(400, message=ex)
        except KeyError as ex:
            self.send_error(404, message=ex)




