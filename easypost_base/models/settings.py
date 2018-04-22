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
    easypost_label_format = fields.Selection(LABEL_FORMATS, "Easypost Label Format", default='pdf',
                                             related='company_id.easypost_label_format')
    shipping_responsible_id = fields.Many2one(comodel_name='res.users', ondelete='set null',
                                              related='company_id.shipping_responsible_id',
                                              string='Responsible for Shipping', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)


class ResCompany(models.Model):
    _inherit = "res.company"

    easypost_key = fields.Char(string="Easypost API Key")
    easypost_label_format = fields.Selection(LABEL_FORMATS, "Easypost Label Format", default='pdf', )
    shipping_responsible_id = fields.Many2one(comodel_name='res.users', ondelete='set null',
                                              string='Responsible for Shipping')
