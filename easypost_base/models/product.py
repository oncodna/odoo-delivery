# -*- coding: utf-8 -*-
##############################################################################
#
#    OncoDNA
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#
##############################################################################

import os
from ast import literal_eval

from odoo import models, fields, api
from odoo.addons.easypost_base.models.carrier import set_field_ep_carriers_selection


class ProductTemplate(models.Model):
    _inherit = "product.template"

    description_delivery = fields.Text("Description for Delivery", help="Used for customs info")


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    @api.model
    def _setup_base(self, partial):
        super(ProductPackaging, self)._setup_base(partial)
        if self.env["easypost_base.carrier"]._fields:
            set_field_ep_carriers_selection(self.env, self._fields["package_carrier_type"])

    @api.model
    def _setup_complete(self):
        super(ProductPackaging, self)._setup_complete()
        self.refresh_packaging()

    @api.model
    def refresh_packaging(self, delivery_type=None):
        set_field_ep_carriers_selection(self.env, self._fields["package_carrier_type"])
        with open(os.path.join(os.path.dirname(__file__), "../data/packages.py")) as packages_file:
            packages_dic = literal_eval(packages_file.read())
            for carrier in packages_dic:
                ep_carrier = self.env["easypost_base.carrier"].create({"name": carrier})
                if delivery_type and ep_carrier.code != delivery_type:
                    continue
                for pack_name in packages_dic[carrier]:
                    exists = self.search([("package_carrier_type", "=", ep_carrier.code), ("name", "=", pack_name)])
                    if not exists and ep_carrier.installed:
                        self.sudo().create(
                            {
                                "name": pack_name,
                                "shipper_package_code": pack_name,
                                "package_carrier_type": ep_carrier.code,
                            }
                        )
