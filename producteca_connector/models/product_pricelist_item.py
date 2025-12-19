from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    def write(self, vals):
        price_fields = [
            'fixed_price', 'percent_price', 'price_discount', 
            'price_surcharge', 'price_min_margin', 'price_max_margin',
            'compute_price', 'base', 'base_pricelist_id'
        ]
        
        price_changed = any(field in vals for field in price_fields)
        
        items_to_sync = []
        if price_changed:
            for item in self:
                affected_products = self._get_affected_products(item)
                if affected_products:
                    items_to_sync.append({
                        'pricelist': item.pricelist_id,
                        'products': affected_products
                    })
        
        result = super(ProductPricelistItem, self).write(vals)
        
        if price_changed and items_to_sync:
            self._trigger_price_sync(items_to_sync)
        
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProductPricelistItem, self).create(vals_list)
        
        items_to_sync = []
        for record in records:
            affected_products = self._get_affected_products(record)
            if affected_products:
                items_to_sync.append({
                    'pricelist': record.pricelist_id,
                    'products': affected_products
                })
        
        if items_to_sync:
            self._trigger_price_sync(items_to_sync)
        
        return records

    def unlink(self):
        items_to_sync = []
        for item in self:
            affected_products = self._get_affected_products(item)
            if affected_products:
                items_to_sync.append({
                    'pricelist': item.pricelist_id,
                    'products': affected_products
                })
        
        result = super(ProductPricelistItem, self).unlink()
        
        if items_to_sync:
            self._trigger_price_sync(items_to_sync)
        
        return result

    def _get_affected_products(self, item):
        ProductProduct = self.env['product.product']
        
        if item.product_tmpl_id:
            products = item.product_tmpl_id.product_variant_ids
        elif item.product_id:
            products = item.product_id
        elif item.categ_id:
            products = ProductProduct.search([
                ('categ_id', 'child_of', item.categ_id.id)
            ])
        else:
            return ProductProduct
        
        products_with_connection = products.filtered(
            lambda p: p.producteca_connection_ids
        )
        
        return products_with_connection

    def _trigger_price_sync(self, items_to_sync):
        for item_data in items_to_sync:
            pricelist = item_data['pricelist']
            products = item_data['products']
            
            _logger.info(
                f"Iniciando sincronización de precios para {len(products)} productos "
                f"debido a cambios en pricelist '{pricelist.name}'"
            )
            
            for product in products:
                pricelist._sync_product_price_on_change(product.id, specific_pricelist_id=pricelist.id)
