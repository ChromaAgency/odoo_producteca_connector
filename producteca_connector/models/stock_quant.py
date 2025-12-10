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
        if not warehouse_name:
            _logger.warning(f"Cannot update stock for product {self.product_id.default_code}: warehouse {self.location_id.warehouse_id.name} has no Producteca warehouse name configured")
            return
        
        stock_data = {"warehouse": warehouse_name}
        stock_data["quantity"] = self.quantity
        
        producteca_body = {
            "sku": self.product_id.default_code,
            "stocks": [stock_data]
        }
        if connection.producteca_id:
            producteca_body.update({
                "id": connection.producteca_id
            })
        client = account.get_client()
        product = client.Product
        product.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        product.synchronize(producteca_body)

    def sync_product_stock_to_producteca(self, connection_id):
        """Synchronize stock for a specific product to Producteca.
        
        This method collects stock quantities from all configured warehouses
        for a given product and sends them to Producteca in a single API call.
        
        Args:
            connection_id (int): Producteca product connection ID to sync
            
        Returns:
            bool: True if sync was successful, False otherwise
        """
        connection = self.env['producteca.product.connections'].browse(connection_id)
        
        if not connection.exists():
            return _logger.error(f"Connection {connection_id} not found")
        
        product = connection.product_id
        account = connection.producteca_account_id
        
        if not product.exists() or not account.exists():
            return _logger.error(f"Product or Account not found for connection {connection_id}")
        
        all_warehouses = account.warehouse_ids | account.default_warehouse_id
        
        stocks_data = []
        for warehouse in all_warehouses:
            warehouse_name = warehouse._get_producteca_warehouse_name(account)
            if not warehouse_name:
                _logger.warning(f"Warehouse {warehouse.name} has no Producteca warehouse name configured")
                continue
            
            quants = self.search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
                ('location_id.warehouse_id', '=', warehouse.id)
            ])
            
            total_quantity = sum(quants.mapped('quantity'))
            
            stocks_data.append({
                "warehouse": warehouse_name,
                "quantity": total_quantity
            })
        
        if not stocks_data:
            _logger.warning(f"No stock data to sync for product {product.default_code}")
            return False
        
        producteca_body = {
            "sku": product.default_code,
            "stocks": stocks_data
        }
        
        if connection.producteca_id:
            producteca_body["id"] = connection.producteca_id
        
        try:
            client = account.get_client()
            product_service = client.Product
            product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist
            product_service.synchronize(producteca_body)
            _logger.info(f"Successfully synced stock for product {product.default_code} to Producteca")
            return True
        except Exception as e:
            _logger.error(f"Error syncing stock for product {product.default_code} to Producteca: {str(e)}")
            return False

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
