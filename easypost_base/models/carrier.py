# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, api, _
from .tools import ep_exec
import urllib2
import base64


class EasypostCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.multi
    @api.depends('delivery_type')
    def _is_easypost(self):
        for carrier in self:
            carrier.is_easypost = carrier.delivery_type.startswith("ep_")

    easypost_account = fields.Char(string='Easypost Account Number', copy=False, help='Begins with "ca_"')
    is_easypost = fields.Boolean(string='Easypost Carrier', compute="_is_easypost")

    def ep_send_shipping(self, pickings):
        res = []
        for picking in pickings:
            picking.ep_shipment_create()
            # TODO: let the user choose among rates
            # TODO: let the user buy an insurance
            shipment = picking.ep_shipment_buy()
            log_message = (_("Shipment created into %s <br/> <b>Tracking Number : </b>%s") %
                           (self.name, shipment.tracking_code))
            file_name, label_data = picking.ep_postage_label(shipment=shipment)
            picking.message_post(body=log_message, attachments=[(file_name, label_data)])
            shipping_data = {
                'exact_price': shipment.selected_rate.rate,
                'tracking_number': shipment.tracking_code
            }
            res = res + [shipping_data]
        return res

    def ep_get_tracking_link(self, pickings):
        res = []
        for picking in pickings:
            res += [picking.ep_shipment().tracker.public_url]
        return res

    def ep_convert_currency(self, amount, to_currency_code):
        order_currency = self.currency_id or self.company_id.currency_id
        to_currency = self.env['res.currency'].search([('name', '=ilike', to_currency_code)])
        if to_currency and to_currency != order_currency:
            return order_currency.compute(amount, to_currency)
        return amount

    def ep_get_shipping_price_from_so(self, orders):
        res = []
        for order in orders:
            ep_shipment = order.ep_shipment_create()
            rate = ep_shipment.lowest_rate().rate
            price = order.ep_convert_currency(rate.rate, rate.currency)
            res = res + [price]
        return res

    def ep_cancel_shipment(self, picking):
        ep_exec(picking.ep_shipment().refund)
        picking.write({'carrier_tracking_ref': '',
                       'carrier_price': 0.0})
