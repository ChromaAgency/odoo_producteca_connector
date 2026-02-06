from odoo import models, fields, api
import logging
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    last_producteca_quantity = fields.Float(string="Last Producteca Quantity", default=0.0, copy=False)

    def _update_stock_in_producteca(self, quant_id):
        """Update stock in Producteca for all active connections.
        
        This method syncs stock changes to ALL active Producteca accounts that have
        connections to this product. If the product is connected to multiple accounts,
        all of them will receive the stock update.
        """
        self.ensure_one()
        
        connections = self.product_id.producteca_connection_ids.filtered(
            lambda c: c.producteca_account_id.active
        )
        
        if not connections:
            return
        
        quant_rec = self.env['stock.quant'].browse(quant_id)
        
        if quant_rec.last_producteca_quantity == self.quantity:
            _logger.info(f"Stock for product {self.product_id.default_code} unchanged ({self.quantity}), skipping update to all Producteca accounts")
            return
        
        sync_success = False
        
        for connection in connections:
            account = connection.producteca_account_id
            
            if not account.is_odoo_able_to_update_producteca_stock:
                continue
            
            all_warehouses = account.warehouse_ids | account.default_warehouse_id
            if self.location_id.warehouse_id not in all_warehouses:
                continue
            
            warehouse_name = self.location_id.warehouse_id._get_producteca_warehouse_name(account)
            if not warehouse_name:
                _logger.warning(f"Cannot update stock for product {self.product_id.default_code}: warehouse {self.location_id.warehouse_id.name} has no Producteca warehouse name configured for account {account.account_name}")
                continue
            
            stock_data = {"warehouse": warehouse_name, "quantity": self.quantity}
            
            producteca_body = {
                "sku": self.product_id.default_code,
                "stocks": [stock_data]
            }
            if connection.producteca_id:
                producteca_body.update({
                    "id": connection.producteca_id
                })
            
            try:
                client = account.get_client()
                product = client.Product
                product.create_if_it_doesnt_exist = account.create_if_dosnt_exist
                product.synchronize(producteca_body)
                sync_success = True
                _logger.info(f"Successfully updated stock for product {self.product_id.default_code} in Producteca account {account.account_name} for quantity {stock_data['quantity']} in warehouse {warehouse_name}")
            except Exception as e:
                _logger.error(f"Error updating stock for product {self.product_id.default_code} in account {account.account_name}: {str(e)}")
                continue
        
        if sync_success:
            quant_rec.last_producteca_quantity = self.quantity

    def _check_and_sync_parent_kits(self):
        """Check if this product is a component of any kit (BoM phantom) and sync those kits.
        
        When a component's stock changes, we need to update the kit's stock in Producteca
        because the kit's availability depends on its components.
        
        A product can be part of multiple kits, so we process all of them.
        The stock calculation for kits is handled automatically by Odoo's qty_available.
        """
        self.ensure_one()
        
        bom_lines = self.env['mrp.bom.line'].search([
            ('product_id', '=', self.product_id.id),
            ('bom_id.type', '=', 'phantom')
        ])
        
        if not bom_lines:
            return
        
        processed_kits = set()
        
        for bom_line in bom_lines:
            bom = bom_line.bom_id
            kit_product = bom.product_id if bom.product_id else bom.product_tmpl_id.product_variant_ids[:1]
            
            if not kit_product or kit_product.id in processed_kits:
                continue
            
            processed_kits.add(kit_product.id)
            
            if not kit_product.is_producteca_product or not kit_product.producteca_connection_ids:
                continue
            
            for connection in kit_product.producteca_connection_ids.filtered(lambda c: c.producteca_account_id.active):
                self.env['stock.quant'].with_delay().sync_product_stock_to_producteca(connection.id)
        
        return True


    def sync_product_stock_to_producteca(self, connection_id):
        connection = self.env['producteca.product.connections'].browse(connection_id)
        
        if not connection.exists():
            return _logger.error(f"Connection {connection_id} not found")
        
        product = connection.product_id.sudo()
        account = connection.producteca_account_id.sudo()
        
        if not product.exists() or not account.exists():
            return _logger.error("Product or Account not found")

        all_warehouses = account.warehouse_ids | account.default_warehouse_id
        stocks_data = []
        
        for warehouse in all_warehouses:
            warehouse_name = warehouse._get_producteca_warehouse_name(account)
            
            if not warehouse_name:
                continue
                
            root_location_id = warehouse.view_location_id.id
            
            if not root_location_id:
                _logger.warning(f"Warehouse {warehouse.name} has no view location defined")
                continue

            qty = product.with_context(location=root_location_id).qty_available
            
            _logger.info(f"Almacén {warehouse.name}: Stock calculado {qty}")

            stocks_data.append({
                "warehouse": warehouse_name,
                "quantity": qty  
            })
            
        if not stocks_data:
            return False
            
        producteca_body = {
            "sku": product.default_code,
            "stocks": stocks_data,
        }
        
        if connection.producteca_id:
            producteca_body["id"] = connection.producteca_id
        
        try:
            client = account.get_client()
            product_service = client.Product
            product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist
            product_service.synchronize(producteca_body)
            _logger.info(f"Success: Synced {product.default_code} to Producteca")
            return True
        except Exception as e:
            _logger.error(f"Sync Error for {product.default_code}: {str(e)}")
            return False

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.location_id.usage == 'internal' and rec.product_id.is_producteca_product:
            rec.with_delay()._update_stock_in_producteca(rec.id)
        return rec

    def write(self, vals):
        _ = super().write(vals)
        for rec in self:
            if rec.location_id.usage == 'internal' and rec.product_id.is_producteca_product and 'quantity' in vals:
                rec.with_delay()._update_stock_in_producteca(rec.id)
            elif rec.location_id.usage == 'internal' and not rec.product_id.is_producteca_product and 'quantity' in vals:
                rec._check_and_sync_parent_kits()
        return _
