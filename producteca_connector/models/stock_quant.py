from odoo import models, fields, api
import logging
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _update_stock_in_producteca(self):
        self.ensure_one()
        # We should handle many products at once
        # for connection in producteca_connections:
        producteca_connection = self.env['producteca.product.connections'].sudo().search([('product_id', '=', self.product_id.id)], limit=1)
        producteca_body = {"code": str(self.product_id.id), "stocks": [{"quantity": self.quantity,
                           "available_quantity": self.available_quantity, "warehouse": self.location_id.producteca_warehouse_name}]}
        producteca_body.update({
            "variation_id": int(producteca_connection.producteca_variation_id)
        })
        account = producteca_connection.producteca_account_id
        client = account.get_client()
        product = client.Product
        product.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        product.synchronize(producteca_body)

    # TODO Handle create

    def write(self, vals):
        _ = super().write(vals)
        for rec in self:
            if rec.location_id.usage == 'internal' and rec.product_id.is_producteca_product and 'quantity' in vals:
                rec.with_delay()._update_stock_in_producteca()
        return _

