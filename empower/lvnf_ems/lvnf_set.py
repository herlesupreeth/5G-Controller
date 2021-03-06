#!/usr/bin/env python3
#
# Copyright (c) 2016 Roberto Riggio
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

"""LVNF EMS SET command."""

from uuid import UUID

from empower.core.lvnf import LVNF
from empower.core.module import Module
from empower.lvnf_ems import PT_LVNF_SET_REQUEST
from empower.lvnf_ems import PT_LVNF_SET_RESPONSE
from empower.core.module import ModuleLVNFPWorker

from empower.main import RUNTIME


class LVNFSet(Module):
    """LVNF Set object."""

    MODULE_NAME = "lvnf_get"
    REQUIRED = ['module_type', 'worker', 'tenant_id', 'lvnf', 'handler',
                'value']

    def __init__(self):

        super().__init__()

        self.__lvnf = None
        self.__handler = None
        self.value = None
        self.samples = None
        self.retcode = None

    def __eq__(self, other):

        return super().__eq__(other) and \
            self.lvnf == other.lvnf and \
            self.handler == other.handler and \
            self.value == other.value

    @property
    def handler(self):
        """Return the handler name."""

        return self.__handler

    @handler.setter
    def handler(self, handler):
        """Set the handler name."""

        tenant = RUNTIME.tenants[self.tenant_id]
        lvnf = tenant.lvnfs[self.lvnf]

        if handler not in lvnf.image.handlers:
            raise KeyError("Handler %s not found" % handler)

        self.__handler = handler

    @property
    def lvnf(self):
        return self.__lvnf

    @lvnf.setter
    def lvnf(self, value):
        self.__lvnf = UUID(str(value))

    def to_dict(self):
        """Return a JSON-serializable representation of this object."""

        out = super().to_dict()

        out['lvnf_id'] = self.lvnf_id
        out['handler'] = self.handler
        out['samples'] = self.samples
        out['retcode'] = self.retcode

        return out

    def run_once(self):
        """Send out handler requests."""

        if self.tenant_id not in RUNTIME.tenants:
            return

        tenant = RUNTIME.tenants[self.tenant_id]

        if self.lvnf not in tenant.lvnfs:
            self.log.error("LVNF %s not found.", self.lvnf)
            return

        lvnf = tenant.lvnfs[self.lvnf]

        if not lvnf.cpp.connection:
            return

        handler_req = {'module_id': self.module_id,
                       'lvnf_id': self.lvnf,
                       'tenant_id': self.tenant_id,
                       'handler': lvnf.image.handlers[self.handler],
                       'value': self.value}

        lvnf.cpp.connection.send_message(PT_LVNF_SET_REQUEST, handler_req)

    def handle_response(self, response):
        """Handle an incoming LVNF_SET_RESPONSE message.
        Args:
            response, a LVNF_SET_RESPONSE message
        Returns:
            None
        """

        tenant_id = UUID(response['tenant_id'])
        lvnf_id = UUID(response['lvnf_id'])

        tenant = RUNTIME.tenants[tenant_id]

        if lvnf_id not in tenant.lvnfs:
            return

        # update this object
        if response['retcode'] != 200:
            error = "%s (%s)" % (response['retcode'], response['samples'])
            self.log.error("Error accessing %s: %s", self.handler, error)
            return

        self.retcode = response['retcode']
        self.samples = response['samples']

        # call callback
        self.handle_callback(self)


class LVNFSetWorker(ModuleLVNFPWorker):
    """ LVNF Set worker. """

    pass


def lvnf_set(**kwargs):
    """Create a new module."""

    return RUNTIME.components[LVNFSetWorker.__module__].add_module(**kwargs)


def bound_lvnf_set(self, **kwargs):
    """Create a new module (app version)."""

    kwargs['tenant_id'] = self.tenant.tenant_id
    kwargs['lvnf'] = self.lvnf
    kwargs['every'] = -1
    return lvnf_set(**kwargs)

setattr(LVNF, LVNFSet.MODULE_NAME, bound_lvnf_set)


def launch():
    """ Initialize the module. """

    return LVNFSetWorker(LVNFSet, PT_LVNF_SET_RESPONSE)
