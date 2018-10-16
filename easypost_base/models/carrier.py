# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, api, _, exceptions
from .tools import ep_exec


class EasypostCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.multi
    @api.depends('delivery_type')
    def _is_easypost(self):
        for carrier in self:
            carrier.is_easypost = carrier.delivery_type.startswith("ep_")

    easypost_account = fields.Char(string='Easypost Account Number', copy=False, help='Begins with "ca_"')
    is_easypost = fields.Boolean(string='Easypost Carrier', compute="_is_easypost")
    delivery_days = fields.Integer(string='Delivery Days',
                                   help="If you provide a number of days, the system will select the cheapest "
                                        "delivery service with a lower or equal number of days for delivery")
    delivery_date_guaranteed = fields.Boolean(string='Guaranteed Delivery Date',
                                              help="Check this box if you want the system to select a service with a "
                                                   "guaranteed delivery window")

    def _get_preferred_rate(self, ep_shipment):
        rates = ep_shipment.rates
        if self.delivery_days:
            rates = filter(lambda r: r.delivery_days <= self.delivery_days, rates)
        if self.delivery_date_guaranteed:
            rates = filter(lambda r: r.delivery_date_guaranteed, rates)
        if not rates:
            raise exceptions.ValidationError(_("No rate satisfying your preferences were provided by the carrier"))
        return min(rates, key=lambda r: float(r.rate))

    def ep_send_shipping(self, pickings):
        res = []
        for picking in pickings:
            ep_shipment = picking.ep_shipment_create()
            # TODO: let the user choose among rates
            # TODO: let the user buy an insurance
            rate = self._get_preferred_rate(ep_shipment)
            picking.ep_shipment_buy(rate_ref=rate.id)
            log_message = (_("Shipment created into %s <br/> <b>Tracking Number : </b>%s") %
                           (self.name, ep_shipment.tracking_code))
            file_name, label_data = picking.ep_postage_label(shipment=ep_shipment)
            picking.message_post(body=log_message, attachments=[(file_name, label_data)])
            shipping_data = {
                'exact_price': ep_shipment.selected_rate.rate,
                'tracking_number': ep_shipment.tracking_code
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
