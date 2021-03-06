# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, api, exceptions, _
from .tools import ep_call, EPMapper, EPMapping, ep_convert_weight, ep_convert_dimension


def get_weight(operation):
    total_weight = operation.product_qty * operation.product_id.weight
    return ep_convert_weight(total_weight)


def get_value(operation):
    picking = operation.picking_id
    picking_currency = picking.sale_id.currency_id or picking.company_id.currency_id
    company_currency = picking.company_id.currency_id
    value = operation.product_qty * operation.product_id.standard_price
    return company_currency.compute(value, picking_currency) or 0.1


def get_description(operation):
    product = operation.product_id
    return product.description_delivery or product.name


EP_CUSTOMSITEM_MAPPER = EPMapper(
    EPMapping("description", "self", convert_fun=lambda operation, _v: get_description(operation), required=True),
    EPMapping("quantity", 'product_qty', convert_fun=lambda _op, value: str(int(value))),
    EPMapping("weight", 'self', required=True, convert_fun=lambda operation, _v: get_weight(operation)),
    EPMapping("value", 'self', required=True, convert_fun=lambda operation, _v: get_value(operation)),
    EPMapping("hs_tariff_number", 'product_id.hs_code'),
    EPMapping("origin_country", 'picking_id.company_id.country_id.code'),
)


class PackOperation(models.Model):
    _inherit = "stock.pack.operation"

    def ep_customsitem_create(self):
        kwargs = EP_CUSTOMSITEM_MAPPER.convert(self, check_missing=True)
        return kwargs
        # return ep_call(self.env, "CustomsItem.create", **kwargs)
