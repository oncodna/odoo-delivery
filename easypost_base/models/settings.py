# -*- coding: utf-8 -*-
##############################################################################
#
#    OncoDNA
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#
##############################################################################

from odoo import models, fields, api


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    easypost_key = fields.Char(string="Easypost API Key", related='company_id.easypost_key')


class ResCompany(models.Model):
    _inherit = "res.company"

    easypost_key = fields.Char(string="Easypost API Key")
