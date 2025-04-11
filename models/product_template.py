from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_producteca_product = fields.Boolean(string="Is Producteca Product")