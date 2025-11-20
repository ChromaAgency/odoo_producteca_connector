from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    producteca_connection_ids = fields.One2many(
        'producteca.product.connections',
        'product_id',
        string='Producteca Connections',
        help="Connections between this product variant and Producteca marketplace variations."
    )
