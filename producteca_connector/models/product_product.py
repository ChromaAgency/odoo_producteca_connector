from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    producteca_connection_ids = fields.One2many(
        'producteca.product.connections',
        'product_id',
        string='Producteca Connections',
        help="Connections between this product variant and Producteca marketplace variations."
    )

    def write(self, vals):
        connections_to_unlink = self.env['producteca.product.connections']
        if 'active' in vals and not vals['active']:
            connections_to_unlink = self.with_context(active_test=False).mapped(
                'producteca_connection_ids'
            )

        result = super().write(vals)

        if connections_to_unlink:
            connections_to_unlink.sudo().unlink()

        return result
