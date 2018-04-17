# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, _
import urllib2
import base64


class EasypostCarrier(models.Model):
    _inherit = 'delivery.carrier'

    easypost_account = fields.Char(string='Easypost Account Number', copy=False)

    def ep_send_shipping(self, pickings):
        res = []
        for picking in pickings:
            picking.ep_shipment_create()
            # TODO: let the user choose among rates
            # TODO: let the user buy an insurance
            shipment = picking.ep_shipment_buy()
            log_message = (_("Shipment created into %s <br/> <b>Tracking Number : </b>%s") %
                           (self.carrier_id.name, shipment.tracking_code))
            label_fmt = picking.company_id.easypost_label_format or 'pdf'
            label_content = urllib2.urlopen(shipment.postage_label.label_url, timeout=5).read()
            label_data = base64.b64encode(label_content)
            file_name = 'EasypostLabel-%s.%s' % (shipment.tracking_code, label_fmt)
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

    def ep_get_shipping_price_from_so(self, orders):
        res = []
        for order in orders:
            ep_shipment = order.ep_shipment_create()
            price = ep_shipment.lowest_rate().rate
            res = res + [price]
        return res

    def ep_cancel_shipment(self, picking):
        picking.ep_shipment().refund()
        picking.write({'carrier_tracking_ref': '',
                       'carrier_price': 0.0})
