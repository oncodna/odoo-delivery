# -*- coding: utf-8 -*-
##############################################################################
#
#    OncoDNA
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#
##############################################################################

from odoo import models, fields, api, exceptions, _
from .tools import ep_call, EPMapper, EPMapping

"""
residential	false	Residential delivery indicator
carrier_facility	ONDC	The specific designation for the address (only relevant if the address is a carrier facility)
federal_tax_id	1234567890	Federal tax identifier of the person or organization
state_tax_id	9876543210	State tax identifier of the person or organization
verify	[delivery, zip4]	The verifications to perform when creating. verify_strict takes precedence
verify_strict	[delivery, zip4]	The verifications to perform when creating. The failure of any of these 
verifications causes the whole request to fail"""

EP_PARTNER_MAPPER = EPMapper(
    EPMapping("street1", "street", required=True),
    EPMapping("street2"),
    EPMapping("city", required=True),
    EPMapping("state", "state_id.name"),
    EPMapping("zip", required=True),
    EPMapping("country", 'country_id.code', required=True),
    EPMapping("name", 'name', convert_fun=lambda partner, value: value if not partner.is_company else False),
    EPMapping("company", 'name', convert_fun=lambda partner, value: value if partner.is_company else False),
    EPMapping("phone", 'phone', required=True, convert_fun=lambda partner, value: value or partner.mobile),
    EPMapping("email"),
)


class Partner(models.Model):
    _inherit = "res.partner"

    def ep_address_create(self, verify=False):
        kwargs = EP_PARTNER_MAPPER.convert(self, check_missing=True)
        if verify:
            kwargs["verify"] = ["delivery"]
        return kwargs
        # return ep_call(self.env, "Address.create", **kwargs)
