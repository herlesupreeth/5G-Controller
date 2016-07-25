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


""" THIS MODULE WORKER IS NOT USED"""



"""UE RRC Measurement module."""

from empower.core.vbsp import VBSP
from empower.datatypes.etheraddress import EtherAddress
from empower.core.module import ModuleVBSPPWorker
from empower.core.module import Module
from protobuf_to_dict import protobuf_to_dict
from empower.main import RUNTIME
import empower.vbspp.messages.progran_pb2 as progran_pb2
import empower.vbspp.messages.header_pb2 as header_pb2
import empower.vbspp.messages.stats_messages_pb2 as stats_messages_pb2
from empower.vbspp import MAC_STATS_TYPE
from empower.vbspp import MAC_STATS_REPORT_FREQ
from empower.vbspp import MAC_CELL_STATS_TYPES
from empower.vbspp import MAC_UE_STATS_TYPES
from empower.vbspp import PRT_MAC_STATS_RESPONSE
from empower.vbspp import TIMER_IDS

import empower.logger
LOG = empower.logger.get_logger()

from empower.core.ue import UE
from empower.core.module import Module
from empower.core.module import ModuleVBSPPEventWorker
from empower.vbspp import PRT_UE_RRC_MEASUREMENTS_RESPONSE
from empower.main import RUNTIME


class UERRCMeasurements(Module):
    """UE RRC Measurements worker."""

    MODULE_NAME = "ue_rrc_measurements"

    def __eq__(self, other):

        return super().__eq__(other) and self.rnti == other.rnti

    def handle_response(self, measurements_response):
        """ Handle an Measurements response message.

        Args:
            measurements_response, a RRC Measurements report message

        Returns:
            None
        """

        measurements_response_dict = protobuf_to_dict(measurements_response)[PRT_UE_RRC_MEASUREMENTS_RESPONSE]
        measurements = measurements_response_dict["measurements"]

        try:
            rnti = measurements_response_dict["rnti"]
            ue = self.vbsp.ues[rnti]
        except KeyError:
            LOG.error(" Unknown UE to VBSP (%s)", (self.vbsp_id))
            return

        ue.PCell_rsrp = measurements["PCell_rsrp"]
        ue.PCell_rsrq = measurements["PCell_rsrq"]

        if "meas_result_neigh_cells" in measurements:
            meas_result_neigh_cells = measurements["meas_result_neigh_cells"]
            for measurement_RAT in meas_result_neigh_cells:
                for measurement in meas_result_neigh_cells[measurement_RAT]:
                    ue.rrc_measurements[measurement["phys_cell_id"]] = {"measId": measurements["measId"],
                                                                        "RAT_type": measurement_RAT,
                                                                        "rsrp": measurement["meas_result"]["rsrp"],
                                                                        "rsrq": measurement["meas_result"]["rsrq"]
                                                                        }

        self.handle_callback(self)

    def to_dict(self):
        """ Return a JSON-serializable."""

        out = super().to_dict()

        # out['vbsp'] = self.vbsp
        # out['mac_stats_req'] = self.mac_stats_req
        # out['mac_stats'] = self.mac_stats_reply

        return out


class UERRCMeasurementsWorker(ModuleVBSPPEventWorker):
    """ Counter worker. """

    pass


def ue_rrc_measurements(**kwargs):
    """Create a new module."""

    return RUNTIME.components[UERRCMeasurementsWorker.__module__].add_module(**kwargs)


def bound_ue_rrc_measurements(self, **kwargs):
    """Create a new module (app version)."""

    kwargs['tenant_id'] = 
    return ue_rrc_measurements(**kwargs)


setattr(UE, UERRCMeasurements.MODULE_NAME, bound_ue_rrc_measurements)


def launch():
    """Initialize the module."""

    return UERRCMeasurementsWorker(UERRCMeasurements, PRT_UE_RRC_MEASUREMENTS_RESPONSE)
