from producteca import ProductecaClient
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    producteca_pricelist_name = fields.Char(string="Producteca Pricelist Name")

    @api.constrains('producteca_pricelist_name')
    def _check_producteca_name_not_default(self):
        """No permitir 'Default' como nombre de lista de precios, se maneja automáticamente"""
        for record in self:
            if record.producteca_pricelist_name and record.producteca_pricelist_name.lower() == 'default':
                raise ValidationError(
                    _("Cannot use 'Default' as Producteca Pricelist Name. "
                      "The default pricelist is handled automatically by the system.")
                )

    def _get_producteca_pricelist_name(self, account):
        """Obtiene el nombre correcto para la pricelist en producteca"""
        if account.default_pricelist_id and self.id == account.default_pricelist_id.id:
            return "Default"
        return self.producteca_pricelist_name



    def _sync_single_product_price(self, account_data, sync_data):
        """Método que se ejecuta en la cola para sincronizar un producto individual"""
        
        client = ProductecaClient(api_key=account_data['api_key'], token=account_data['bearer_token'])
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account_data['create_if_dosnt_exist']
        
        _logger.info(f"Syncing price for product: {sync_data}")

        result = product_service.synchronize(sync_data)
        _logger.info(f"Sync result: {result}")
        return result

    def _sync_prices_for_account(self, account_id, pricelist_id=None, use_list_price=False):
        """Sincroniza precios para una cuenta específica y una pricelist específica o usando list_price"""
        account = self.env['producteca.account'].browse(account_id)
        
        account_data = {
            'api_key': account.api_key,
            'bearer_token': account.bearer_token,
            'create_if_dosnt_exist': account.create_if_dosnt_exist
        }
        
        producteca_connections = self.env['producteca.product.connections'].search([
            ('producteca_account_id', '=', account.id)
        ])
        
        for connection in producteca_connections:
            template = connection.product_tmpl_id
            
            if not template:
                continue
            
            if use_list_price:
                if template.list_price:
                    # Use first variant for image/code reference
                    first_variant = template.product_variant_ids[0] if template.product_variant_ids else None
                    if not first_variant:
                        continue
                        
                    sync_data = {
                        'sku': first_variant.default_code,
                        'prices': [{
                            'amount': template.list_price,
                            'currency': "Usd" if account.company_id.currency_id.id == self.env.ref('base.USD').id else "Local",
                            'priceList': 'Default'
                        }]
                    }
                    self.with_delay()._sync_single_product_price(account_data, sync_data)
            else:
                pricelist = self.browse(pricelist_id)
                pricelist_name = pricelist._get_producteca_pricelist_name(account)
                
                if not pricelist_name:
                    _logger.warning(f"Pricelist {pricelist.name} (ID: {pricelist.id}) no tiene producteca_pricelist_name configurado. Saltando sincronización.")
                    continue
                
                # Use first variant for price calculation
                first_variant = template.product_variant_ids[0] if template.product_variant_ids else None
                if not first_variant:
                    continue
                    
                price = pricelist._get_product_price(first_variant, 1)
                if price:
                    sync_data = {
                        'sku': first_variant.default_code,
                        'prices': [{
                            'amount': price,
                            'currency': "Usd" if pricelist.currency_id.id == self.env.ref('base.USD').id else "Local",
                            'priceList': pricelist_name
                        }]
                    }
                    self.with_delay()._sync_single_product_price(account_data, sync_data)

    @api.model  
    def cron_sync_all_pricelists_to_producteca(self):
        producteca_accounts = self.env['producteca.account'].search([
            ('active', '=', True),
            ('is_odoo_able_to_update_producteca_prices', '=', True)
        ])
        
        for account in producteca_accounts:
        
            if account.default_pricelist_id:
                account.default_pricelist_id.with_delay()._sync_prices_for_account(account.id, account.default_pricelist_id.id)
            else:
                self.with_delay()._sync_prices_for_account(account.id, use_list_price=True)
            
            for pricelist in account.pricelist_ids:
                if pricelist.producteca_pricelist_name:
                    pricelist.with_delay()._sync_prices_for_account(account.id, pricelist.id)
                else:
                    _logger.warning(f"Pricelist {pricelist.name} (ID: {pricelist.id}) no tiene producteca_pricelist_name configurado. Saltando sincronización.")
