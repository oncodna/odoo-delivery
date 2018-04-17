# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, api, exceptions, _
from .tools import ep_call, EPRuleSet, EPRule, ep_convert_weight, ep_convert_dimension


def get_package_details(picking, field):
    pack_type = picking.package_ids[:1].packaging_id
    if not pack_type:
        return False
    if pack_type.package_carrier_type.lower() == picking.carrier_id.code.lower():
        return pack_type.shipper_package_code if field == "predefined_package" else False
    return ep_convert_dimension(pack_type[field])


EP_PARCEL_RULESET = EPRuleSet(
    EPRule("weight", "shipping_weight", required=True, convert_fun=lambda picking, value: ep_convert_weight(value)),
    EPRule("length", 'package_ids', convert_fun=lambda picking, value: get_package_details(picking, "length")),
    EPRule("width", 'package_ids', convert_fun=lambda picking, value: get_package_details(picking, "width")),
    EPRule("height", 'package_ids', convert_fun=lambda picking, value: get_package_details(picking, "height")),
    EPRule("predefined_package", 'package_ids',
           convert_fun=lambda picking, value: get_package_details(picking, "predefined_package")),
)


def get_address_from(picking, location_partner):
    partner = location_partner or picking.company_id.partner_id
    return partner.ep_address_create(verify=True)


EP_SHIPMENT_RULESET = EPRuleSet(
    EPRule("mode", "company_id.easypost_mode", required=True),
    EPRule("to_address", 'partner_id', required=True,
           convert_fun=lambda picking, partner: partner.ep_address_create(verify=True)),
    EPRule("from_address", 'location_id.partner_id', required=True, convert_fun=get_address_from),
    EPRule("parcel", 'self', required=True, convert_fun=lambda picking, _p: picking.ep_parcel_create),
    EPRule("carrier_accounts", 'carrier_id.easypost_account',
           convert_fun=lambda picking, ep_account: [ep_account] if ep_account else []),
)


class Picking(models.Model):
    _inherit = "stock.picking"

    easypost_shipment_ref = fields.Char(string='Easypost Shipment Reference', copy=False)

    def ep_parcel_create(self):
        kwargs = EP_PARCEL_RULESET.convert(self, check_missing=True)
        return ep_call(self.env, "Parcel.create", **kwargs)

    def ep_shipment(self):
        return ep_call(self.env, "Shipment.retrieve", self.easypost_shipment_ref)

    def ep_shipment_buy(self, rate_ref=None, insurance=None):
        ep_shipment = self.ep_shipment()
        kwargs = {}
        if insurance:
            kwargs['insurance'] = insurance
        rate = ep_shipment.lowest_rate()
        if rate_ref:
            rates = filter(lambda r: r.id == rate_ref, ep_shipment.rates)
            if rates:
                rate = rates[0]
        ep_shipment = ep_shipment.buy(rate=rate, **kwargs)
        self.carrier_tracking_ref = ep_shipment.tracking_code
        return ep_shipment

    def ep_shipment_create(self):
        self.ensure_one()
        if self.easypost_shipment_ref:
            ep_shipment = self.ep_shipment()
        else:
            kwargs = EP_SHIPMENT_RULESET.convert(self, check_missing=True)
            currency = self.sale_id.currency_id or self.company_id.currency_id
            kwargs['options'] = {
                "currency": currency.name
            }
            ep_shipment = ep_call(self.env, "Shipment.create", **kwargs)
            self.easypost_shipment_ref = ep_shipment.id
        return ep_shipment
