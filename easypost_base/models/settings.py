# -*- coding: utf-8 -*-
##############################################################################
#
#    OncoDNA
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#
##############################################################################

from odoo import models, fields, api

LABEL_FORMATS = [('png', 'PNG'), ('pdf', 'PDF'), ('zpl', 'ZPL'), ('epl2', 'EPL2')]


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    easypost_key = fields.Char(string="Easypost API Key", related='company_id.easypost_key')
    easypost_mode = fields.Selection([('test', 'Test'), ('production', 'Production')], "Easypost Mode", default='test',
                                     related='company_id.easypost_mode')
    easypost_label_format = fields.Selection(LABEL_FORMATS, "Easypost Label Format", default='pdf',
                                             related='company_id.easypost_label_format')


class ResCompany(models.Model):
    _inherit = "res.company"

    easypost_key = fields.Char(string="Easypost API Key")
    easypost_mode = fields.Selection([('test', 'Test'), ('production', 'Production')], "Easypost Mode", default='test')
    easypost_label_format = fields.Selection(LABEL_FORMATS, "Easypost Label Format", default='pdf', )
