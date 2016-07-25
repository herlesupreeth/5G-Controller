#!/usr/bin/env python3
#
# Copyright (c) 2015, Roberto Riggio
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

"""VBSP Protocol Server."""

from tornado.tcpserver import TCPServer
from empower.core.pnfpserver import BaseTenantPNFDevHandler
from empower.core.pnfpserver import BasePNFDevHandler
from empower.restserver.restserver import RESTServer
from empower.core.pnfpserver import PNFPServer
from empower.vbspp.vbspmacstatshandler import VBSPMACStatsHandler
from empower.vbspp.uerrcmeasurementshandler import UERRCMeasurementsHandler
from empower.vbspp.uehandler import UEHandler
from empower.persistence.persistence import TblVBSP
from empower.core.vbsp import VBSP
from empower.vbspp import PRT_TYPES
from empower.vbspp import PRT_TYPES_HANDLERS
from empower.vbspp.vbspconnection import VBSPConnection
from empower.vbspp import DEFAULT_CONTROLLER_AGENT_IPv4_ADDRESS
from empower.vbspp import DEFAULT_PORT
from empower.vbspp import MAC_STATS_TYPE
from empower.vbspp import MAC_STATS_REPORT_FREQ
from empower.vbspp import MAC_CELL_STATS_TYPES
from empower.vbspp import MAC_UE_STATS_TYPES
import empower.vbspp.messages.stats_messages_pb2 as stats_messages_pb2

from empower.main import RUNTIME

import empower.logger
LOG = empower.logger.get_logger()


MAC_STATS_TYPE.update({
    "complete": stats_messages_pb2.PRST_COMPLETE_STATS,
    "cell": stats_messages_pb2.PRST_CELL_STATS,
    "ue": stats_messages_pb2.PRST_UE_STATS
})

MAC_STATS_REPORT_FREQ.update({
    "once": stats_messages_pb2.PRSRF_ONCE,
    "periodical": stats_messages_pb2.PRSRF_PERIODICAL,
    # "continuous": stats_messages_pb2.PRSRF_CONTINUOUS,
    "off": stats_messages_pb2.PRSRF_OFF
})

MAC_CELL_STATS_TYPES.update({
    "noise_interference": stats_messages_pb2.PRCST_NOISE_INTERFERENCE
})

MAC_UE_STATS_TYPES.update({
    "buffer_status_report": stats_messages_pb2.PRUST_BSR,
    "power_headroom_report": stats_messages_pb2.PRUST_PRH,
    "rlc_buffer_status_report": stats_messages_pb2.PRUST_RLC_BS,
    "mac_ce_buffer_status_report": stats_messages_pb2.PRUST_MAC_CE_BS,
    "mac_ce_buffer_status_report": stats_messages_pb2.PRUST_MAC_CE_BS,
    "downlink_cqi_report": stats_messages_pb2.PRUST_DL_CQI,
    "paging_buffer_status_report": stats_messages_pb2.PRUST_PBS,
    "uplink_cqi_report": stats_messages_pb2.PRUST_UL_CQI
})

class TenantVBSPHandler(BaseTenantPNFDevHandler):
    """TenantVBSP Handler."""

    HANDLERS = [r"/api/v1/tenants/([a-zA-Z0-9-]*)/vbsps/?",
                r"/api/v1/tenants/([a-zA-Z0-9-]*)/vbsps/([a-zA-Z0-9:]*)/?"]


class VBSPHandler(BasePNFDevHandler):
    """VBSP Handler."""

    HANDLERS = [(r"/api/v1/vbsps/?"),
                (r"/api/v1/vbsps/([a-zA-Z0-9:]*)/?")]


class VBSPServer(PNFPServer, TCPServer):
    """Exposes the VBSP API."""

    PNFDEV = VBSP
    TBL_PNFDEV = TblVBSP

    def __init__(self, port, prt_types, prt_types_handlers):

        PNFPServer.__init__(self, prt_types, prt_types_handlers)
        TCPServer.__init__(self)

        self.port = int(port)
        self.ues = {}
        self.connection = None

        # self.listen(self.port, "127.0.0.1")
        self.listen(self.port)

    def handle_stream(self, stream, address):
        LOG.info('Incoming connection from %r and %r', address, stream)
        self.connection = VBSPConnection(stream, address, server=self)


def launch(port=DEFAULT_PORT):
    """Start VBSP Server Module."""

    server = VBSPServer(port, PRT_TYPES, PRT_TYPES_HANDLERS)

    rest_server = RUNTIME.components[RESTServer.__module__]
    rest_server.add_handler_class(TenantVBSPHandler, server)
    rest_server.add_handler_class(VBSPHandler, server)
    rest_server.add_handler_class(VBSPMACStatsHandler, server)
    rest_server.add_handler_class(UEHandler, server)
    rest_server.add_handler_class(UERRCMeasurementsHandler, server)

    LOG.info("VBSP Server available at %u", server.port)
    return server
