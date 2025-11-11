from odoo import models, fields, api
import logging
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _update_stock_in_producteca(self):
        self.ensure_one()
        
        producteca_connection = self.env['producteca.product.connections'].sudo().search([
            ('product_variant_ids', 'in', self.product_id.id)
        ], limit=1)
        account = producteca_connection.producteca_account_id
        if self.location_id.warehouse_id not in account.warehouse_ids:
            return
        _logger.info("producteca_id: %s", producteca_connection.producteca_id)
        producteca_body = {"sku": self.product_id.default_code, "stocks": [{"quantity": self.quantity,
                           "available_quantity": self.available_quantity, "warehouse": self.location_id.warehouse_id.producteca_warehouse_name}]}
        if producteca_connection.producteca_id:
            producteca_body.update({
                "id": producteca_connection.producteca_id
            })
        client = account.get_client()
        product = client.Product
        product.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        _logger.info(product.synchronize(producteca_body))

    # TODO Handle create

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.location_id.usage == 'internal' and rec.product_id.is_producteca_product:
            rec.with_delay()._update_stock_in_producteca()
        return rec

    def write(self, vals):
        _ = super().write(vals)
        for rec in self:
            if rec.location_id.usage == 'internal' and rec.product_id.is_producteca_product and 'quantity' in vals:
                rec.with_delay()._update_stock_in_producteca()
        return _
