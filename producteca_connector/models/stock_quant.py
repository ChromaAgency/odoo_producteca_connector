from odoo import models, fields, api
import logging
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _update_stock_in_producteca(self):
        self.ensure_one()
        
        connection = self.product_id.producteca_connection_ids.filtered(
            lambda c: c.producteca_account_id.active
        )[:1]
        
        if not connection:
            return
            
        account = connection.producteca_account_id
        
        if not account.is_odoo_able_to_update_producteca_stock:
            return
        
        all_warehouses = account.warehouse_ids | account.default_warehouse_id
        if self.location_id.warehouse_id not in all_warehouses:
            return
        
        warehouse_name = self.location_id.warehouse_id._get_producteca_warehouse_name(account)
        
        producteca_body = {"sku": self.product_id.default_code, "stocks": [{"quantity": self.quantity,
                           "available_quantity": self.available_quantity, "warehouse": warehouse_name}]}
        if connection.producteca_id:
            producteca_body.update({
                "id": connection.producteca_id
            })
        client = account.get_client()
        product = client.Product
        product.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        product.synchronize(producteca_body)

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
