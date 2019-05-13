# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, api, _, exceptions
from .tools import ep_exec
from collections import OrderedDict
import os
from ast import literal_eval

EP_PREFIX = 'ep_'


def set_field_ep_carriers_selection(env, field):
    added = []
    selection_dic = OrderedDict(field.selection)
    ep_carriers = env['easypost_base.carrier'].search([('installed', '=', True)])
    for (code, _name) in field.selection:
        if code.startswith(EP_PREFIX) and code != EP_PREFIX and code not in ep_carriers.mapped("code") \
                and code in selection_dic:
            del selection_dic[code]
    for carrier in ep_carriers:
        if carrier.code not in selection_dic:
            selection_dic[carrier.code] = carrier.name + " (Easypost)"
            added.append(carrier)
    field.selection = selection_dic.items()


class EasypostCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.model
    def _setup_complete(self):
        super(EasypostCarrier, self)._setup_complete()
        if self.env['easypost_base.carrier']._fields:
            set_field_ep_carriers_selection(self.env, self._fields['delivery_type'])

    @api.multi
    @api.depends('delivery_type')
    def _get_easypost_carrier(self):
        for carrier in self:
            carrier.is_easypost = (carrier.delivery_type or "").startswith(EP_PREFIX)
            carrier.ep_carrier_id = self.env['easypost_base.carrier'].search([('code', '=', carrier.delivery_type)])

    delivery_type = fields.Selection(selection_add=[(EP_PREFIX, "Easypost (all carriers)")])
    easypost_account = fields.Char(string='Easypost Account Number', copy=False, help='Begins with "ca_"')
    is_easypost = fields.Boolean(string='Easypost Carrier', compute="_get_easypost_carrier")
    delivery_days = fields.Integer(string='Delivery Days',
                                   help="If you provide a number of days, the system will select the cheapest "
                                        "delivery service with a lower or equal number of days for delivery")
    delivery_date_guaranteed = fields.Boolean(string='Guaranteed Delivery Date',
                                              help="Check this box if you want the system to select a service with a "
                                                   "guaranteed delivery window")
    ep_carrier_id = fields.Many2one('easypost_base.carrier', string="Provider", compute="_get_easypost_carrier")
    preferred_service_ids = fields.Many2many('easypost_base.service', 'ep_carrier_service_rel', 'carrier_id',
                                             'service_id', string='Preferred Services', )

    @api.multi
    def name_get(self):
        result = []
        default = dict(super(EasypostCarrier, self).name_get())
        for carrier in self:
            if carrier.is_easypost and not 'easypost' in default[carrier.id].lower():
                name = default[carrier.id] + " (Easypost)"
            else:
                name = default[carrier.id]
            result.append((carrier.id, name))
        return result

    @api.onchange('delivery_type')
    def filter_services(self):
        self.preferred_service_ids = False
        deli_dom = [('ep_carrier_id', '=', self.ep_carrier_id.id)]
        if self.delivery_type == EP_PREFIX:
            deli_dom = []
        return {'domain': {'preferred_service_ids': deli_dom}}

    def _get_preferred_rate(self, ep_shipment):
        rates = ep_shipment.rates
        if self.delivery_days:
            rates = filter(lambda r: r.delivery_days <= self.delivery_days, rates)
        if self.delivery_date_guaranteed:
            rates = filter(lambda r: r.delivery_date_guaranteed, rates)
        if self.preferred_service_ids:
            rates = filter(lambda r: r.service in self.preferred_service_ids.mapped('name'), rates)
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

    def __getattribute__(self, name):
        magic_methods = ['send_shipping', 'get_tracking_link', 'get_shipping_price_from_so', 'cancel_shipment']
        if any((name.startswith(EP_PREFIX) and name.endswith(m)) for m in magic_methods):
            try:
                return super(EasypostCarrier, self).__getattribute__(name)
            except AttributeError:
                ep_carriers = self.env['easypost_base.carrier'].search([('installed', '=', True)])
                for method in magic_methods:
                    if any((name == code + "_" + method) for code in ep_carriers.mapped('code')):
                        return super(EasypostCarrier, self).__getattribute__(EP_PREFIX + method)
                raise
        return super(EasypostCarrier, self).__getattribute__(name)


class EasypostService(models.Model):
    _name = 'easypost_base.service'

    @api.depends("name")
    def _get_code(self):
        for car in self:
            car.code = "%s%s" % (EP_PREFIX, car.name.lower().replace(' ', '_'))

    ep_carrier_id = fields.Many2one('easypost_base.carrier', string="Provider")
    name = fields.Char("Name", required=True)
    code = fields.Char("Code", compute="_get_code", store=True)

    @api.model
    def refresh_services(self, delivery_type=None):
        set_field_ep_carriers_selection(self.env, self.env['delivery.carrier']._fields["delivery_type"])
        with open(os.path.join(os.path.dirname(__file__), "../data/services.py")) as services_file:
            services_dic = literal_eval(services_file.read())
            for carrier in services_dic:
                ep_carrier = self.env['easypost_base.carrier'].create({'name': carrier})
                if delivery_type and ep_carrier.code != delivery_type:
                    continue
                for srv_name in services_dic[carrier]:
                    exists = self.search([('ep_carrier_id', '=', ep_carrier.id), ('name', '=', srv_name)])
                    if not exists and ep_carrier.installed:
                        self.sudo().create({'name': srv_name, 'ep_carrier_id': ep_carrier.id})


class EasypostProvider(models.Model):
    _name = 'easypost_base.carrier'
    _order = 'name'

    @api.depends("name")
    def _get_code(self):
        for car in self:
            car.code = "%s%s" % (EP_PREFIX, car.name.lower().replace(' ', '_'))

    name = fields.Char("Name", required=True)
    code = fields.Char("Code", compute="_get_code", store=True)
    installed = fields.Boolean("Installed")

    @api.model
    def create(self, vals):
        exists = self.search([('name', '=', vals['name'])])
        if exists:
            return exists
        return super(EasypostProvider, self).create(vals)
