from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    producteca_id = fields.Char(string='Producteca ID')