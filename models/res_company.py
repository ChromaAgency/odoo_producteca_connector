from odoo import models, fields, api
from odoo.tools.translate import _

class ResCompany(models.Model):
    _inherit = 'res.company'

    producteca_account_ids = fields.One2many('producteca.account', 'company_id', string='Producteca Accounts')