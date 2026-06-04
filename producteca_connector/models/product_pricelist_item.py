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
                if not self._is_pricelist_in_producteca_account(item.pricelist_id):
                    continue
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
            if not self._is_pricelist_in_producteca_account(record.pricelist_id):
                continue
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
            if not self._is_pricelist_in_producteca_account(item.pricelist_id):
                continue
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

    def _is_pricelist_in_producteca_account(self, pricelist):
        """Verifica si una pricelist está asignada a alguna cuenta de Producteca activa con permisos."""
        accounts = self.env['producteca.account'].search([
            '|',
            ('default_pricelist_id', '=', pricelist.id),
            ('pricelist_ids', 'in', [pricelist.id]),
            ('active', '=', True),
            ('is_odoo_able_to_update_producteca_prices', '=', True)
        ])
        return bool(accounts)

    def _get_affected_products(self, item):
        products = self._get_products_from_item(item)
        return products.filtered(lambda p: p.producteca_connection_ids)
    
    def _get_products_from_item(self, item):
        ProductProduct = self.env['product.product']
        
        if item.base == 'pricelist' and item.base_pricelist_id:
            base_items = self.env['product.pricelist.item'].search([
                ('pricelist_id', '=', item.base_pricelist_id.id)
            ])
            
            all_products = ProductProduct.browse()
            has_global_item = False
            
            for base_item in base_items:
                if base_item.product_tmpl_id:
                    all_products |= base_item.product_tmpl_id.product_variant_ids
                elif base_item.product_id:
                    all_products |= base_item.product_id
                elif base_item.categ_id:
                    all_products |= ProductProduct.search([
                        ('categ_id', 'child_of', base_item.categ_id.id)
                    ])
                elif base_item.base != 'pricelist':
                    has_global_item = True
                    break
            
            if has_global_item:
                return ProductProduct.search([
                    ('producteca_connection_ids', '!=', False)
                ])
            
            if all_products:
                return all_products
            
            return ProductProduct.browse()
        
        if item.product_tmpl_id:
            return item.product_tmpl_id.product_variant_ids
        elif item.product_id:
            return item.product_id
        elif item.categ_id:
            return ProductProduct.search([
                ('categ_id', 'child_of', item.categ_id.id)
            ])
        else:
            return ProductProduct.browse()

    def _trigger_price_sync(self, items_to_sync):
        for item_data in items_to_sync:
            pricelist_id = item_data['pricelist'].id
            products = item_data['products']
            
            _logger.info(
                f"Iniciando sincronización de precios para {len(products)} productos "
                f"debido a cambios en pricelist ID: {pricelist_id}"
            )
            
            for product in products:
                self.env['product.pricelist'].with_delay()._sync_product_price_on_change(product.id, pricelist_id)
