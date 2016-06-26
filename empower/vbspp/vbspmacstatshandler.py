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

"""VBSP MAC Statistics Handler."""

import tornado.web
import tornado.httpserver
import uuid

from empower.datatypes.etheraddress import EtherAddress
from empower.main import RUNTIME
from empower.vbspp import MAX_NUM_CCs
from empower.vbspp import MAC_STATS_TYPE
from empower.vbspp import MAC_STATS_REPORT_FREQ
from empower.vbspp import MAC_CELL_STATS_TYPES
from empower.vbspp import MAC_UE_STATS_TYPES
from empower.restserver.apihandlers import EmpowerAPIHandlerAdminUsers

import empower.logger
LOG = empower.logger.get_logger()


class VBSPMACStatsHandler(EmpowerAPIHandlerAdminUsers):
    """VBSPMACStats Handler . Used to start, stop vbsp mac stats reporting."""

    HANDLERS = [r"/api/v1/tenants/([a-zA-Z0-9-]*)/vbsps/([a-zA-Z0-9:]*)/mac_stats/?"]

    def post(self, *args, **kwargs):
        """ Get the MAC stats as per the given request for a specified VBSP.

        Args:
            tenant_id: the tenant identifier
            vbsp_id: the vbsp identifier

        Example URLs:
            GET /api/v1/tenants/daa2b515-8aed-4e6b-b171-2ff4dd12b768/vbsps/11:22:33:44:55:66/mac_stats

        data: '{
                    "version" : "1.0",
                    "stats_request_config": {
                        "report_type": "complete", // ("complete", "cell", "ue")
                        "report_frequency": "once", // ("periodical", "once", "off")
                        "timer_xid": 0, // Value range (0 - 253), used only in case of stopping (off) the periodic reporting
                        "periodicity": 5, // ("number of sub frames interval = number of milliseconds)
                        "report_config": {
                            "ue_report_type": {
                                "ue_report_flags": ["buffer_status_report", "power_headroom_report"...], // Refer MAC_UE_STATS_TYPES
                                "ue_rnti": [86aed, 6eadc, ...] // Leave blank in case of "complete" report_type
                            },
                            "cell_report_type": {
                                "cell_report_flags": ["noise_interference"..], // Refere MAC_CELL_STATS_TYPES
                                "cc_id": [0, 1, ...] // number of component carrier in a specified vbsp, currently only one CC is supported
                            }
                        }
                    }
               }'
        """

        from empower.vbspp import TIMER_IDS

        try:

            if len(args) < 2 or len(args) > 2:
                raise ValueError("Invalid URL")

            request = tornado.escape.json_decode(self.request.body)

            if "version" not in request:
                raise ValueError("missing version element")

            if "stats_request_config" not in request:
                raise ValueError("missing stats_request_config element")

            if "report_type" not in request["stats_request_config"]:
                raise ValueError("missing report_type element")

            if request["stats_request_config"]["report_type"] not in MAC_STATS_TYPE:
                raise ValueError("Invalid report_type element")

            if "report_frequency" not in request["stats_request_config"]:
                raise ValueError("missing report_frequency element")

            if request["stats_request_config"]["report_frequency"] not in MAC_STATS_REPORT_FREQ:
                raise ValueError("Invalid report_frequency element")

            if request["stats_request_config"]["report_frequency"] == "periodical" and "periodicity" not in request["stats_request_config"]:
                raise ValueError("missing periodicity element")

            if request["stats_request_config"]["report_frequency"] == "off" and "timer_xid" not in request["stats_request_config"]:
                raise ValueError("missing timer_xid element")

            if request["stats_request_config"]["report_frequency"] == "off":
                if request["stats_request_config"]["timer_xid"] not in TIMER_IDS:
                    raise ValueError("Invalid timer_xid element")
                else:
                    TIMER_IDS.remove(request["stats_request_config"]["timer_xid"])

            vbsp = None

            tenant_id = uuid.UUID(args[0])
            tenant = RUNTIME.tenants[tenant_id]
            vbsp = tenant.vbsps[EtherAddress(args[1])]

            if request["stats_request_config"]["report_frequency"] != "off":
                if "report_config" not in request["stats_request_config"]:
                    raise ValueError("missing report_config element")

                if "ue_report_type" not in request["stats_request_config"]["report_config"]:
                    raise ValueError("missing ue_report_type element")

                if "cell_report_type" not in request["stats_request_config"]["report_config"]:
                    raise ValueError("missing cell_report_type element")

                if "ue_report_flags" not in request["stats_request_config"]["report_config"]["ue_report_type"] and \
                    len(request["stats_request_config"]["report_config"]["ue_report_type"]["ue_report_flags"]) == 0:
                    
                    raise ValueError("missing ue_report_flags element")

                for flag in request["stats_request_config"]["report_config"]["ue_report_type"]["ue_report_flags"]:
                    if flag not in MAC_UE_STATS_TYPES:
                        raise ValueError("Invalid ue_report_flag type")
                        break

                if "cell_report_flags" not in request["stats_request_config"]["report_config"]["cell_report_type"] and \
                    len(request["stats_request_config"]["report_config"]["cell_report_type"]["cell_report_flags"]) == 0:
                    
                    raise ValueError("missing cell_report_flags element")

                for flag in request["stats_request_config"]["report_config"]["cell_report_type"]["cell_report_flags"]:
                    if flag not in MAC_CELL_STATS_TYPES:
                        raise ValueError("Invalid cell_report_flag type")
                        break

                if request["stats_request_config"]["report_type"] == "cell":
                    if len(request["stats_request_config"]["report_config"]["cell_report_type"]["cc_id"]) == 0:
                        raise ValueError("missing cc_id element")

                    for cc in request["stats_request_config"]["report_config"]["cell_report_type"]["cc_id"]:
                        if cc >= MAX_NUM_CCs:
                            raise ValueError("Invalid CC (Component Carrier) id value")
                            break
 
                if request["stats_request_config"]["report_type"] == "ue":
                    if len(vbsp.ues) == 0:
                        raise ValueError("No UEs are registered to vbsp")

                    if len(request["stats_request_config"]["report_config"]["ue_report_type"]["ue_rnti"]) == 0:
                        raise ValueError("missing ue_rnti element")

                    for rnti in request["stats_request_config"]["report_config"]["ue_report_type"]["ue_rnti"]:
                        if rnti not in vbsp.ues:
                            raise ValueError("Invalid rnti value of ue or ue does not exist")
                            break

            new_module = vbsp.vbsp_mac_stats(every= -1, callback=self.vbsp_mac_stats_callback, mac_stats_req=request, tenant_id=tenant_id)

            if request["stats_request_config"]["report_frequency"] == "off":
                new_module.worker.remove_module(new_module.module_id)

        except KeyError as ex:
            self.send_error(404, message=ex)
        except ValueError as ex:
            self.send_error(400, message=ex)
        
        self.set_header("Location", "/api/v1/tenants/%s/%s" %
                        (tenant_id,
                        "vbsp_mac_stats"))
        self.set_status(200, None)

    def vbsp_mac_stats_callback(self, mac_stats_module):
        """ New stats available. """

        LOG.info("New MAC Stats received from %s" % mac_stats_module.vbsp)

        if mac_stats_module.mac_stats_req["stats_request_config"]["report_frequency"] == "once":
            mac_stats_module.worker.remove_module(mac_stats_module.module_id)
