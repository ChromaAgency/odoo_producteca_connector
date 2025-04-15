from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_producteca_product = fields.Boolean(string="Is Producteca Product")


    def write(self, vals):
        _logger.info('write vals %s',vals)
        _ = super().write(vals)
        producteca_queue = []
        for rec in self:
            if rec.is_producteca_product and 'list_price' in vals:
                for product in rec.product_variant_ids:
                    producteca_queue.append({
                        "producteca_body": vals['list_price'],
                        "producteca_method": "update",
                        "model": "product.product",
                        "odoo_item_id": product.id
                    })
        if producteca_queue:
            self.env['producteca.queue'].create(producteca_queue)
        return _
        