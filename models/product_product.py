from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_producteca_product = fields.Boolean(string="Is Producteca Product", related='product_tmpl_id.is_producteca_product', store=True)
    is_already_sync = fields.Boolean(string="Is Already Sync", readonly=True, copy=False)


    def write(self, vals):
        _ = super().write(vals)
        producteca_queue = []
        for rec in self:
            if rec.is_producteca_product and 'list_price' in vals:
                producteca_queue.append({
                    "producteca_body": vals['list_price'],
                    "producteca_method": "update",
                    "model": "product.product",
                    "odoo_item_id": rec.id
                })
        if producteca_queue:
            self.env['producteca.queue'].sudo().create(producteca_queue)
        return _

