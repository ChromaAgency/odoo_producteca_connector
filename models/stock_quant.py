from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    #TODO Handle create

    def write(self, vals):
        queue_to_create = []
        _ = super().write(vals)
        for rec in self:
            if rec.location_id.usage == 'internal' and rec.product_id.is_producteca_product and 'quantity' in vals:
                queue_to_create.append({
                    "producteca_body": {"code":str(rec.product_id.id),
                        "stocks": [{"quantity": vals['quantity'], "available_quantity": rec.available_quantity, "warehouse": rec.location_id.name}]},
                    "producteca_method": "update",
                    "model": "stock.quant",
                    "odoo_item_id": rec.product_id.id
                })
        if queue_to_create:
            self.env['producteca.queue'].sudo().create(queue_to_create)
        return _
    