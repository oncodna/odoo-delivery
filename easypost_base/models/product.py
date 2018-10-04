# -*- coding: utf-8 -*-
##############################################################################
#
#    OncoDNA
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#
##############################################################################

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    description_delivery = fields.Text('Description for Delivery', help="Used for customs info")
