from odoo import models, fields, api
from odoo.tools.translate import _


class ProductecaConnections(models.Model):
    _name = 'producteca.connections'
    _description = 'Producteca Connections'
    
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    producteca_variation_id = fields.Char(string='Producteca Variation ID')
    producteca_id = fields.Char(string='Producteca ID', required=True)
