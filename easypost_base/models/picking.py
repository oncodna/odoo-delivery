# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, api, exceptions, _
from .tools import ep_call, ep_exec, EPMapper, EPMapping, ep_convert_weight, ep_convert_dimension, \
    ep_check_shipment_rates, ep_postage_label, ep_shipment_buy
from odoo.exceptions import ValidationError
import base64

"""
contents_type = The type of item you are sending. You pass one of the following: 'merchandise', 'returned_goods',
'documents', 'gift', 'sample', 'other'.
contents_explanation = If you specify ‘other’ in the ‘contents_type’ attribute, you must supply a brief description in 
this attribute.
restriction_type = Describes if your shipment requires any special treatment / quarantine when entering the country. 
You pass one of the following: 'none', 'other', 'quarantine', 'sanitary_phytosanitary_inspection'.
restriction_comments = If you specify ‘other’ in the “restriction_type attribute”, you must supply a brief description 
of what is required.

eel_pfc = When shipping outside the US, you need to provide either an Exemption and Exclusion Legend (EEL) code or a 
Proof of Filing Citation (PFC). Which you need is based on the value of the goods being shipped."""

EP_CUSTOMSINFO_MAPPER = EPMapper(
    EPMapping("customs_items", "pack_operation_product_ids", required=True,
           convert_fun=lambda _p, operations: operations.mapped(lambda o: o.ep_customsitem_create())),
    EPMapping("contents_type", "contents_type", required=True),
    EPMapping("contents_explanation", "contents_explanation"),
    EPMapping("restriction_type", "self", required=True, convert_fun=lambda _p, _v: 'none'),
    EPMapping("customs_certify", "self", convert_fun=lambda _p, _v: True),
    EPMapping("customs_signer", "company_id.shipping_responsible_id.name", required=True),
    EPMapping("eel_pfc", "self", convert_fun=lambda _p, _v: "NOEEI 30.37(a)"),  # TODO: improve this
)


def get_package_details(picking, field):
    pack_type = picking.package_ids[:1].packaging_id
    if not pack_type:
        return False
    if pack_type.package_carrier_type.lower() == picking.carrier_id.delivery_type.lower():
        return pack_type.shipper_package_code if field == "predefined_package" else False
    return ep_convert_dimension(pack_type[field]) if field != "predefined_package" else False


EP_PARCEL_MAPPER = EPMapper(
    EPMapping("weight", "shipping_weight", required=True, convert_fun=lambda picking, value: ep_convert_weight(value)),
    EPMapping("length", 'package_ids', convert_fun=lambda picking, value: get_package_details(picking, "length")),
    EPMapping("width", 'package_ids', convert_fun=lambda picking, value: get_package_details(picking, "width")),
    EPMapping("height", 'package_ids', convert_fun=lambda picking, value: get_package_details(picking, "height")),
    EPMapping("predefined_package", 'package_ids',
           convert_fun=lambda picking, value: get_package_details(picking, "predefined_package")),
)


def get_address_from(picking, location_partner):
    partner = location_partner or picking.company_id.partner_id
    return partner.ep_address_create(verify=True)


EP_SHIPMENT_MAPPER = EPMapper(
    EPMapping("mode", "carrier_id.prod_environment", convert_fun=lambda _o, value: 'production' if value else 'test'),
    EPMapping("to_address", 'partner_id', required=True,
           convert_fun=lambda picking, partner: partner.ep_address_create(verify=True)),
    EPMapping("from_address", 'location_id.partner_id', required=True, convert_fun=get_address_from),
    EPMapping("parcel", 'self', required=True, convert_fun=lambda picking, _p: picking.ep_parcel_create()),
    EPMapping("customs_info", 'self', required=True, convert_fun=lambda picking, _p: picking.ep_customsinfo_create()),
    EPMapping("carrier_accounts", 'carrier_id.easypost_account',
           convert_fun=lambda picking, ep_account: [ep_account] if ep_account else []),
    # EPMapping("is_return", 'self', required=True, convert_fun=lambda picking, _p: True),
)


class Picking(models.Model):
    _inherit = "stock.picking"

    easypost_shipment_ref = fields.Char(string='Easypost Shipment Reference', copy=False)
    contents_type = fields.Selection([('documents', 'Documents'), ('gift', 'Gift'), ('merchandise', 'Merchandise'),
                                      ('returned_goods', 'Returned_Goods'), ('sample', 'Sample'),
                                      ('other', 'Other')], string='Contents Type', default="merchandise", required=True)
    contents_explanation = fields.Text(string='Contents Explanation')

    def _check_mandatory_contents_explanation(self):
        for picking in self.filtered(lambda p: p.contents_type in ('other',)):
            if not picking.contents_explanation:
                raise ValidationError(_('Deliveries with contents type "Other" must provide a contents explanation'))

    @api.multi
    def do_new_transfer(self):
        self._check_mandatory_contents_explanation()
        return super(Picking, self).do_new_transfer()

    def ep_postage_label(self, shipment=None, label_format=None):
        ep_shipment = shipment or self.ep_shipment()
        label_format = (label_format or self.company_id.easypost_label_format or 'pdf').lower()
        return ep_postage_label(ep_shipment, carrier=self.carrier_id, label_format=label_format)

    def ep_refresh_label(self, label_format=None):
        ep_shipment = self.ep_shipment()
        log_message = (_("Shipment created into %s <br/> <b>Tracking Number : </b>%s") %
                       (self.name, ep_shipment.tracking_code))
        file_name, label_data = self.ep_postage_label(shipment=ep_shipment, label_format=label_format)
        self.message_post(body=log_message, attachments=[(file_name, label_data)])

    def ep_customsinfo_create(self):
        kwargs = EP_CUSTOMSINFO_MAPPER.convert(self, check_missing=True)
        return kwargs
        # return ep_call(self.env, "CustomsInfo.create", **kwargs)

    def ep_parcel_create(self):
        kwargs = EP_PARCEL_MAPPER.convert(self, check_missing=True)
        return kwargs
        # return ep_call(self.env, "Parcel.create", **kwargs)

    def ep_shipment(self):
        shipment = ep_call(self.env, "Shipment.retrieve", self.easypost_shipment_ref)
        return shipment

    def ep_shipment_buy(self, rate_ref=None, insurance=None):
        ep_shipment = self.ep_shipment()
        ep_shipment_buy(ep_shipment, rate_ref=rate_ref, insurance=insurance)
        self.carrier_tracking_ref = ep_shipment.tracking_code
        return ep_shipment

    def ep_shipment_create(self):
        self.ensure_one()
        if self.easypost_shipment_ref:
            ep_shipment = self.ep_shipment()
        else:
            kwargs = EP_SHIPMENT_MAPPER.convert(self, check_missing=True)
            currency = self.sale_id.currency_id or self.company_id.currency_id
            kwargs['options'] = {
                "currency": currency.name,
            }
            ep_shipment = ep_call(self.env, "Shipment.create", **kwargs)
            self.easypost_shipment_ref = ep_shipment.id
        # ep_shipment.get_rates()
        return ep_shipment
