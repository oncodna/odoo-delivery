# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

from odoo import models, fields, api, exceptions, _
from .tools import ep_call, ep_exec, EPRuleSet, EPRule, ep_convert_weight, ep_convert_dimension
import urllib2
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

EP_CUSTOMSINFO_RULESET = EPRuleSet(
    EPRule("customs_items", "pack_operation_product_ids", required=True,
           convert_fun=lambda _p, operations: operations.mapped(lambda o: o.ep_customsitem_create())),
    EPRule("contents_type", "self", required=True, convert_fun=lambda _p, _v: "merchandise"),  # TODO: improve this
    EPRule("contents_explanation", "self", convert_fun=lambda _p, _v: False),  # TODO
    EPRule("restriction_type", "self", required=True, convert_fun=lambda _p, _v: 'none'),
    EPRule("customs_certify", "self", convert_fun=lambda _p, _v: True),
    EPRule("customs_signer", "company_id.shipping_responsible_id.name", required=True),
    EPRule("eel_pfc", "self", convert_fun=lambda _p, _v: "NOEEI 30.37(a)"),  # TODO: improve this
)


def get_package_details(picking, field):
    pack_type = picking.package_ids[:1].packaging_id
    if not pack_type:
        return False
    if pack_type.package_carrier_type.lower() == picking.carrier_id.delivery_type.lower():
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
    EPRule("mode", "carrier_id.prod_environment", convert_fun=lambda _o, value: 'production' if value else 'test'),
    EPRule("to_address", 'partner_id', required=True,
           convert_fun=lambda picking, partner: partner.ep_address_create(verify=True)),
    EPRule("from_address", 'location_id.partner_id', required=True, convert_fun=get_address_from),
    EPRule("parcel", 'self', required=True, convert_fun=lambda picking, _p: picking.ep_parcel_create()),
    EPRule("customs_info", 'self', required=True, convert_fun=lambda picking, _p: picking.ep_customsinfo_create()),
    EPRule("carrier_accounts", 'carrier_id.easypost_account',
           convert_fun=lambda picking, ep_account: [ep_account] if ep_account else []),
)


class Picking(models.Model):
    _inherit = "stock.picking"

    easypost_shipment_ref = fields.Char(string='Easypost Shipment Reference', copy=False)

    def ep_postage_label(self, shipment=None, label_format=None):
        ep_shipment = shipment or self.ep_shipment()
        label_format = (label_format or self.company_id.easypost_label_format or 'pdf').lower()
        shipment.label(file_format=label_format.upper())
        label_url_attr = "label_%s_url" % label_format if label_format != 'png' else "label_url"
        label_url = getattr(ep_shipment.postage_label, label_url_attr)
        label_content = urllib2.urlopen(label_url, timeout=5).read()
        carrier_code = self.carrier_id.code or "easypost"
        file_name = '%s-%s.%s' % (carrier_code, ep_shipment.tracking_code, label_format)
        return file_name, label_content

    def ep_refresh_label(self, label_format=None):
        ep_shipment = self.ep_shipment()
        log_message = (_("Shipment created into %s <br/> <b>Tracking Number : </b>%s") %
                       (self.name, ep_shipment.tracking_code))
        file_name, label_data = self.ep_postage_label(shipment=ep_shipment, label_format=label_format)
        self.message_post(body=log_message, attachments=[(file_name, label_data)])

    def ep_customsinfo_create(self):
        kwargs = EP_CUSTOMSINFO_RULESET.convert(self, check_missing=True)
        return kwargs
        # return ep_call(self.env, "CustomsInfo.create", **kwargs)

    def ep_parcel_create(self):
        kwargs = EP_PARCEL_RULESET.convert(self, check_missing=True)
        return kwargs
        # return ep_call(self.env, "Parcel.create", **kwargs)

    def ep_shipment(self):
        shipment = ep_call(self.env, "Shipment.retrieve", self.easypost_shipment_ref)
        return shipment

    def ep_shipment_buy(self, rate_ref=None, insurance=None):
        ep_shipment = self.ep_shipment()
        kwargs = {}
        if insurance:
            kwargs['insurance'] = insurance
        if not ep_shipment.rates:
            error_messages = []
            for msg in ep_shipment.messages:
                if msg.type == "rate_error":
                    error_messages.append(msg.message)
            message = _("No rates were received from the carrier.")
            if error_messages:
                message += _(" Errors include:\n\n")
                message += "\n".join(error_messages)
            raise exceptions.UserError(message)
        rate = ep_exec(ep_shipment.lowest_rate)
        if rate_ref:
            rates = filter(lambda r: r.id == rate_ref, ep_shipment.rates)
            if rates:
                rate = rates[0]
        ep_exec(ep_shipment.buy, rate=rate, **kwargs)
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
                "currency": currency.name,
            }
            ep_shipment = ep_call(self.env, "Shipment.create", **kwargs)
            self.easypost_shipment_ref = ep_shipment.id
        # ep_shipment.get_rates()
        return ep_shipment
