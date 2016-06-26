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

"""(VBSP) User Equipment class."""

from empower.datatypes.etheraddress import EtherAddress


import empower.logger
LOG = empower.logger.get_logger()


class UE(object):

    def __init__(self, rnti, vbsp, config, capabilities):

        self.rnti = rnti
        self.ue_id = self.convert_hex_rnti_to_ether_address(self.rnti)
        self.vbsp = vbsp
        self.config = config
        self.capabilities = capabilities
        self.rrc_measurements_config = {}
        self.rrc_measurements = {}
        self.PCell_rsrp = None
        self.PCell_rsrq = None

    def to_dict(self):
        """ Return a JSON-serializable dictionary representing the LVAP """

        return {'rnti': self.rnti,
                'vbsp': self.vbsp.addr,
                'ue_id': self.ue_id,
                'capabilities': self.capabilities,
                'rrc_measurements_config': self.rrc_measurements_config
                }

    def convert_hex_rnti_to_ether_address(self, rnti):

        str_hex_value = format(rnti, 'x')
        padding = '0' * (12 - len(str_hex_value))
        mac_string = padding + str_hex_value
        mac_string_array = [mac_string[i:i+2] for i in range(0, len(mac_string), 2)]

        return EtherAddress(":".join(mac_string_array))

    def __eq__(self, other):
        if isinstance(other, UE):
            return self.rnti == other.rnti
        return False

    def __ne__(self, other):
        return not self.__eq__(other)
