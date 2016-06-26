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

"""VBSP Connection."""

import time
import tornado.ioloop
from construct import Container
from time import sleep

import empower.vbspp.messages.progran_pb2 as progran_pb2
import empower.vbspp.messages.header_pb2 as header_pb2
import empower.vbspp.messages.stats_messages_pb2 as stats_messages_pb2
import empower.vbspp.messages.config_common_pb2 as config_common_pb2
from empower.datatypes.etheraddress import EtherAddress
from empower.vbspp import MESSAGE_SIZE
from empower.vbspp import PRT_VBSP_HELLO
from empower.vbspp import PRT_VBSP_BYE
from empower.vbspp import PRT_UE_STATE_CHANGE
from empower.vbspp import PRT_UE_RRC_MEASUREMENTS_RESPONSE
from empower.vbspp import PRT_VBSP_REGISTER
from empower.vbspp import PROGRAN_VERSION
from empower.vbspp import MAC_STATS_TYPE
from empower.vbspp import MAC_STATS_REPORT_FREQ
from empower.vbspp import MAC_CELL_STATS_TYPES
from empower.vbspp import MAC_UE_STATS_TYPES
from empower.vbspp import TIMER_IDS
from protobuf_to_dict import protobuf_to_dict
from empower.core.ue import UE
from empower.main import RUNTIME

import empower.logger
LOG = empower.logger.get_logger()


class VBSPConnection(object):
    """VBSP Connection.

    Represents a connection to a ENB (EUTRAN Base Station) using
    the VBSP Protocol. One VBSPConnection object is created for every
    ENB in the network. The object implements the logic for handling
    incoming messages. The currently supported messages are:

    Attributes:
        stream: The stream object used to talk with the ENB.
        address: The connection source address, i.e. the ENB IP address.
        server: Pointer to the server object.
        vbsp: Pointer to a VBSP object.
    """

    def __init__(self, stream, addr, server):
        self.stream = stream
        self.addr = addr
        self.server = server
        self.vbsp = None
        self.enb_id = None
        self.vbsp_id = None
        self.xid = None
        self.stream.set_close_callback(self._on_disconnect)
        self.__buffer = b''
        self._hb_interval_ms = 500
        self._hb_worker = tornado.ioloop.PeriodicCallback(self._heartbeat_cb,
                                                          self._hb_interval_ms)
        self._hb_worker.start()
        self._wait()

    def to_dict(self):
        """Return dict representation of object."""

        return self.addr

    def _heartbeat_cb(self):
        """ Check if wtp connection is still active. Disconnect if no hellos
        have been received from the wtp for twice the hello period. """
        if self.vbsp and not self.stream.closed():
            timeout = (self.vbsp.period / 1000) * 3
            if (self.vbsp.last_seen_ts + timeout) < time.time():
                LOG.info('Client inactive %s at %r', self.vbsp.addr, self.addr)
                self.stream.close()

    def create_header(self, xid, eid, message_type, header):

        if not header:
            LOG.error("header parameter is None")

        header.version = PROGRAN_VERSION
        header.type = message_type
        header.xid = xid
        header.eid = eid

    def build_size_message(self, size):

        size_message = Container(length=size)
        return MESSAGE_SIZE.build(size_message)

    def serialize_message(self, message):

        if not message:
            LOG.error("message parameter is None")
            return None

        return message.SerializeToString()

    def deserialize_message(self, serialized_data):

        if not serialized_data:
            LOG.error("Received serialized data is None")
            return None

        msg = progran_pb2.progran_message()
        msg.ParseFromString(serialized_data)

        return msg

    def stream_send(self, message):

        err_code = progran_pb2.NO_ERR

        size = message.ByteSize()
        send_buff = self.serialize_message(message)
        size_message = self.build_size_message(size)

        if send_buff is None:
            err_code = progran_pb2.MSG_ENCODING
            LOG.error("errno %u occured" % err_code)

        # First send the length of the message and then the actual message
        self.stream.write(size_message)
        self.stream.write(send_buff)

        if self.vbsp:
            self.vbsp.downlink_bytes += 4 + size

    def send_echo_request(self, enb_id):

        echo_request = progran_pb2.progran_message()

        self.create_header(self.xid, enb_id, header_pb2.PRPT_ECHO_REQUEST, echo_request.echo_request_msg.header)
        echo_request.msg_dir = progran_pb2.INITIATING_MESSAGE

        LOG.info("Sending echo request message to VBSP %f", self.vbsp.addr)
        self.stream_send(echo_request)

    def _handle_echo_request(self, enb_id, echo_request):

        if echo_request is None:
            LOG.error("Echo request message is null")

        xid = echo_request.echo_request_msg.header.xid

        echo_reply = progran_pb2.progran_message()
        err_code = progran_pb2.NO_ERR

        self.create_header(xid, enb_id, header_pb2.PRPT_ECHO_REPLY,
                           echo_reply.echo_reply_msg.header)

        echo_reply.msg_dir = progran_pb2.SUCCESSFUL_OUTCOME

        LOG.info("Sending echo reply message to VBSP %f", self.vbsp.addr)
        self.stream_send(echo_reply)

    def _on_read(self, line):
        """ Appends bytes read from socket to a buffer. Once the full packet
        has been read the parser is invoked and the buffers is cleared. The
        parsed packet is then passed to the suitable method or dropped if the
        packet type in unknown. """

        self.__buffer = b''

        if line is not None:
            LOG.info("Received message of length %d" % len(line))

            self.__buffer = self.__buffer + line

            if self.vbsp:
                self.vbsp.uplink_bytes += len(line)

            if len(line) == 4: # Checking for size message (4 Bytes)
                size = MESSAGE_SIZE.parse(self.__buffer)
                remaining = size.length
                self.stream.read_bytes(remaining, self._on_read)
                return

            deserialized_msg = self.deserialize_message(line)

            # LOG.info("\n\n\n************ START OF REPLY MESSAGE ********************\n\n\n")

            LOG.info(deserialized_msg.__str__())

            # LOG.info("\n\n\n************ END OF REPLY MESSAGE **********************\n\n\n")

            self._trigger_message(deserialized_msg)
            self._wait()

    def _trigger_message(self, deserialized_msg, callback_data=None):

        msg_type = deserialized_msg.WhichOneof("msg")

        if msg_type == None or msg_type not in self.server.pt_types:

            LOG.error("Unknown message type %u", msg_type)
            return

        while msg_type != PRT_VBSP_HELLO and self.vbsp == None:
            sleep(2)  # Time in seconds.

        handler_name = "_handle_%s" % self.server.pt_types[msg_type]

        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            handler(deserialized_msg)

        if msg_type in self.server.pt_types_handlers:
            for handler in self.server.pt_types_handlers[msg_type]:
                handler(deserialized_msg)

    def convert_hex_enb_id_to_ether_address(self, enb_id):

        str_hex_value = format(enb_id, 'x')
        padding = '0' * (12 - len(str_hex_value))
        mac_string = padding + str_hex_value
        mac_string_array = [mac_string[i:i+2] for i in range(0, len(mac_string), 2)]

        return EtherAddress(":".join(mac_string_array))

    def _handle_ue_state_change(self, ue_state):

        ue_state_dict = protobuf_to_dict(ue_state)[PRT_UE_STATE_CHANGE]
        rnti = ue_state_dict["config"]["rnti"]

        if ue_state_dict["type"] == config_common_pb2.PRUESC_ACTIVATED:
            if "capabilities" not in ue_state_dict["config"]:
                capabilities = {}
            else:
                capabilities = ue_state_dict["config"]["capabilities"]
                del ue_state_dict["config"]["capabilities"]
            del ue_state_dict["config"]["rnti"]
            self.vbsp.ues[rnti] = UE(rnti, self.vbsp, ue_state_dict["config"], capabilities)

        elif ue_state_dict["type"] == config_common_pb2.PRUESC_DEACTIVATED and rnti in self.vbsp.ues:            
            del self.vbsp.ues[rnti]

    def _handle_ue_rrc_measurements_reply(self, measurements_response):

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



    def _handle_hello(self, hello):
        """Handle an incoming HELLO message.
        Args:
            hello, a HELLO message
        Returns:
            None
        """

        if not self.enb_id:
            self.enb_id = hello.hello_msg.header.eid
            self.vbsp_id = self.convert_hex_enb_id_to_ether_address(self.enb_id)
        elif self.enb_id != hello.hello_msg.header.eid:
            LOG.error(" Hello from different ENB with id (%f)", hello.hello_msg.header.eid)
            return

        try:
            vbsp = RUNTIME.vbsps[self.vbsp_id]
        except KeyError:
            LOG.error(" Hello from unknown VBSP (%s)", (self.vbsp_id))
            return

        LOG.info(" Hello from %s , port %s, VBSP %s", self.addr[0], self.addr[1], self.vbsp_id.to_str())

        # If this is a new connection, then send enb status request or enb config request
        if not vbsp.connection:
            # set enb before connection because it is used when the connection
            # attribute of the PNFDev object is set
            self.vbsp = vbsp
            vbsp.connection = self
            self.xid = hello.hello_msg.header.xid + 1
            vbsp.period = 5000 # milliseconds
            self.send_enb_config_request(self.enb_id)

        # Update VBSP params
        # vbsp.period = 5000000
        # wtp.last_seen = hello.seq
        vbsp.last_seen_ts = time.time()
        # self.send_mac_stats_request()

    def send_mac_stats_request(self, enb_id, params, xid):

        stats_request = progran_pb2.progran_message()

        self.create_header(xid, enb_id, header_pb2.PRPT_GET_ENB_CONFIG_REQUEST, stats_request.stats_request_msg.header)
        stats_request.msg_dir = progran_pb2.INITIATING_MESSAGE

        try:
            stats_request_config = params["stats_request_config"]
            stats_request_msg = stats_request.stats_request_msg
            stats_request_msg.type = MAC_STATS_TYPE[stats_request_config["report_type"]]

            if stats_request_msg.type == stats_messages_pb2.PRST_COMPLETE_STATS:

                complete_stats = stats_request_msg.complete_stats_request
                complete_stats.report_frequency = MAC_STATS_REPORT_FREQ[stats_request_config["report_frequency"]]
                complete_stats.sf = stats_request_config["periodicity"]

                cc_report_flag = 0
                ue_report_flag = 0

                if stats_request_config["report_frequency"] != "off":
                    for flag in stats_request_config["report_config"]["cell_report_type"]["cell_report_flags"]:
                        cc_report_flag |= MAC_CELL_STATS_TYPES[flag]            

                    for flag in stats_request_config["report_config"]["ue_report_type"]["ue_report_flags"]:
                        ue_report_flag |= MAC_UE_STATS_TYPES[flag]

                complete_stats.ue_report_flags = ue_report_flag
                complete_stats.cell_report_flags = cc_report_flag

            elif stats_request_msg.type == stats_messages_pb2.PRST_CELL_STATS:
                cell_stats = stats_request_msg.cell_stats_request
                cell_stats.report_frequency = MAC_STATS_REPORT_FREQ[stats_request_config["report_frequency"]]
                cell_stats.sf = stats_request_config["periodicity"]

                cc_report_flag = 0

                for flag in stats_request_config["report_config"]["cell_report_type"]["cell_report_flags"]:
                    cc_report_flag |= MAC_CELL_STATS_TYPES[flag]

                for cc in stats_request_config["report_config"]["cell_report_type"]["cc_id"]:
                    cell_stats.cell.append(cc)

                cell_stats.flags = cc_report_flag

            elif stats_request_msg.type == stats_messages_pb2.PRST_UE_STATS:
                # Periodic reporting not supported here yet
                ue_stats = stats_request_msg.ue_stats_request
                ue_stats.report_frequency = MAC_STATS_REPORT_FREQ[stats_request_config["report_frequency"]]
                ue_stats.sf = stats_request_config["periodicity"]

                ue_report_flag = 0                

                for flag in stats_request_config["report_config"]["ue_report_type"]["ue_report_flags"]:
                    ue_report_flag |= MAC_UE_STATS_TYPES[flag]

                for rnti in stats_request_config["report_config"]["ue_report_type"]["ue_rnti"]:
                    ue_stats.rnti.append(rnti)

                ue_stats.flags = ue_report_flag

        except KeyError as ex:
            return None
        except ValueError as ex:
            return None

        LOG.info("Sending ENB mac stats request message to VBSP %s", self.vbsp.addr)
        self.stream_send(stats_request)

        return 0

    def _handle_enb_config_reply(self, enb_config_reply):

        vbsp = RUNTIME.vbsps[self.vbsp_id]
        vbsp.enb_config = protobuf_to_dict(enb_config_reply)["enb_config_reply_msg"]

    def send_enb_config_request(self, enb_id):

        enb_config_request = progran_pb2.progran_message()

        self.create_header(self.xid, enb_id, header_pb2.PRPT_GET_ENB_CONFIG_REQUEST, enb_config_request.enb_config_request_msg.header)
        enb_config_request.msg_dir = progran_pb2.INITIATING_MESSAGE

        LOG.info("Sending ENB config request message to VBSP %s", self.vbsp.addr)
        self.stream_send(enb_config_request)

    def _wait(self):
        """ Wait for incoming packets on signalling channel """
        self.stream.read_bytes(4, self._on_read)

    def _on_disconnect(self):
        """ Handle WTP disconnection """

        if not self.vbsp:
            return

        LOG.info("VBSP disconnected: %s" % self.vbsp.addr)

        # reset state
        # self.vbsp.last_seen = 0
        self.vbsp.connection = None
        TIMER_IDS = []
        # self.vbsp.ports = {}
        # self.vbsp.supports = ResourcePool()

        # remove hosted LVAPs
        to_be_removed = []
        for vbsp in RUNTIME.vbsps.values():
            if vbsp == self.vbsp:
                to_be_removed.append(vbsp)

        # commented for now by supreeth
        # for vbsp in to_be_removed:
        #     LOG.info("LVAP LEAVE %s (%s)", lvap.addr, lvap.ssid)
        #     for handler in self.server.pt_types_handlers[PT_LVAP_LEAVE]:
        #         handler(lvap)
        #     LOG.info("Deleting LVAP: %s", lvap.addr)
        #     lvap.clear_ports()
        #     del RUNTIME.lvaps[lvap.addr]

    def send_bye_message_to_self(self):
        """Send a unsollicited BYE message to self."""

        for handler in self.server.pt_types_handlers[PRT_VBSP_BYE]:
            handler(self.wtp)

    def send_register_message_to_self(self):
        """Send a REGISTER message to self."""

        for handler in self.server.pt_types_handlers[PRT_VBSP_REGISTER]:
            handler(self.wtp)
