#!/usr/bin/env python3
#
# Copyright (c) 2016 Roberto Riggio, Supreeth Herle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.

from empower.core.app import EmpowerApp
from empower.core.module import Module
from empower.core.module import ModuleVBSPPEventWorker
from empower.vbspp import PRT_ENB_CONFIG_RESPONSE
from empower.main import RUNTIME


class VBSPUp(Module):
    """VBSPUp worker."""

    MODULE_NAME = "vbspup"

    def handle_response(self, enb_config_message):
        """ Handle an ENB Config Message message.

        Args:
            enb_config_message, a ENB Config Message message

        Returns:
            None
        """

        vbsps = RUNTIME.tenants[self.tenant_id].vbsps

        # if caps.wtp not in wtps:
        #     return

        # wtp = wtps[caps.wtp]

        # self.handle_callback(wtp)


class VBSPUpWorker(ModuleVBSPPEventWorker):
    """ Counter worker. """

    pass


def vbspup(**kwargs):
    """Create a new module."""

    return RUNTIME.components[VBSPUpWorker.__module__].add_module(**kwargs)


def app_vbspup(self, **kwargs):
    """Create a new module (app version)."""

    kwargs['tenant_id'] = self.tenant_id
    return vbspup(**kwargs)


setattr(EmpowerApp, VBSPUp.MODULE_NAME, app_vbspup)


def launch():
    """Initialize the module."""

    return VBSPUpWorker(VBSPUp, PRT_ENB_CONFIG_RESPONSE)
