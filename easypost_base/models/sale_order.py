# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, api, exceptions, _
from .tools import ep_call, EPRuleSet, EPRule, ep_convert_weight, ep_convert_dimension


def get_weight(order_lines):
    total_weight = sum([(line.product_id.weight * line.product_qty) for line in order_lines])
    return ep_convert_weight(total_weight)


EP_PARCEL_RULESET = EPRuleSet(
    EPRule("weight", "order_line", required=True, convert_fun=lambda _o, order_lines: get_weight(order_lines)),
)


def get_address_from(order, warehouse_partner):
    partner = warehouse_partner or order.company_id.partner_id
    return partner.ep_address_create(verify=True)


EP_SHIPMENT_RULESET = EPRuleSet(
    EPRule("mode", "carrier_id.prod_environment", convert_fun=lambda _o, value: 'production' if value else 'test'),
    EPRule("to_address", 'partner_shipping_id', required=True,
           convert_fun=lambda order, partner: partner.ep_address_create(verify=True)),
    EPRule("from_address", 'warehouse_id.partner_id', required=True, convert_fun=get_address_from),
    EPRule("parcel", 'self', required=True, convert_fun=lambda order, _o: order.ep_parcel_create()),
    EPRule("carrier_accounts", 'carrier_id.easypost_account',
           convert_fun=lambda picking, ep_account: [ep_account] if ep_account else []),
)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def ep_shipment(self):
        return ep_call(self.env, "Shipment.retrieve", self.easypost_shipment_ref)

    def ep_parcel_create(self):
        kwargs = EP_PARCEL_RULESET.convert(self, check_missing=True)
        return ep_call(self.env, "Parcel.create", **kwargs)

    def ep_shipment_create(self):
        self.ensure_one()
        kwargs = EP_SHIPMENT_RULESET.convert(self, check_missing=True)
        currency = self.sale_id.currency_id or self.company_id.currency_id
        kwargs['options'] = {
            "currency": currency.name
        }
        res = ep_call(self.env, "Shipment.create", **kwargs)
        return res
