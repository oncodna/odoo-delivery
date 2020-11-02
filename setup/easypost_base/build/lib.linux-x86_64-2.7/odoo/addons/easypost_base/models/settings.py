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

    @api.depends('company_id')
    def _get_easypost_carriers(self):
        for setting in self:
            setting.easypost_carrier_ids = self.env['easypost_base.carrier'].search([('installed', '=', True)])

    def _set_easypost_carriers(self):
        for setting in self:
            setting.easypost_carrier_ids.write({'installed': True})
            others = self.env['easypost_base.carrier'].search([('id', 'not in', setting.easypost_carrier_ids.ids)])
            others.write({'installed': False})
        self.env['easypost_base.service'].refresh_services()
        self.env['product.packaging'].refresh_packaging()

    easypost_key = fields.Char(string="Easypost API Key", related='company_id.easypost_key')
    easypost_label_format = fields.Selection(LABEL_FORMATS, "Easypost Label Format", default='pdf',
                                             related='company_id.easypost_label_format')
    shipping_responsible_id = fields.Many2one(comodel_name='res.users', ondelete='set null',
                                              related='company_id.shipping_responsible_id',
                                              string='Responsible for Shipping', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    easypost_carrier_ids = fields.Many2many(comodel_name='easypost_base.carrier', compute='_get_easypost_carriers',
                                            inverse='_set_easypost_carriers', string="Easypost Carriers")


class ResCompany(models.Model):
    _inherit = "res.company"

    easypost_key = fields.Char(string="Easypost API Key")
    easypost_label_format = fields.Selection(LABEL_FORMATS, "Easypost Label Format", default='pdf', )
    shipping_responsible_id = fields.Many2one(comodel_name='res.users', ondelete='set null',
                                              string='Responsible for Shipping')
