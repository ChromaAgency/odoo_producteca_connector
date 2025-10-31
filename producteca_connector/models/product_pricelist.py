from odoo import models, fields, api
from odoo.tools.translate import _
import logging

_logger = logging.getLogger(__name__)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    producteca_pricelist_name = fields.Char(string="Producteca Pricelist Name")

    def _sync_single_product_price(self, account_data, sync_data):
        """Método que se ejecuta en la cola para sincronizar un producto individual"""
        from producteca import ProductecaClient
        
        client = ProductecaClient(api_key=account_data['api_key'], token=account_data['bearer_token'])
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account_data['create_if_dosnt_exist']
        
        _logger.info(f"Syncing price for product: {sync_data}")

        # result = product_service.synchronize(sync_data)
        # _logger.info(f"Sync result: {result}")
        # return result

    def _sync_prices_for_account(self, account_id):
        account = self.env['producteca.account'].browse(account_id)
        
        account_data = {
            'api_key': account.api_key,
            'bearer_token': account.bearer_token,
            'create_if_dosnt_exist': account.create_if_dosnt_exist
        }
        
        pricelist_data = {
            'currency': "Usd" if account.pricelist_to_sync.currency_id.name == 'USD' else "Local",
            'name': account.pricelist_to_sync.producteca_pricelist_name
        }
        
        producteca_connections = self.env['producteca.product.connections'].search([
            ('producteca_account_id', '=', account.id)
        ])
        
        for connection in producteca_connections:
            product = connection.product_id
            
            price = account.pricelist_to_sync._get_product_price(product, 1)
            if price:
                sync_data = {
                    'sku': product.default_code,
                    'name': product.name,
                    'prices': [{
                        'amount': price,
                        'currency': pricelist_data['currency'],
                        'priceList': pricelist_data['name']
                    }]
                }
                
                self.with_delay()._sync_single_product_price(account_data, sync_data)

    @api.model
    def cron_sync_all_pricelists_to_producteca(self):
        producteca_accounts = self.env['producteca.account'].search([
            ('active', '=', True),
            ('is_odoo_able_to_update_producteca_prices', '=', True),
            ('pricelist_to_sync', '!=', False)
        ])
        
        for account in producteca_accounts:
            pricelist = account.pricelist_to_sync
            pricelist._sync_prices_for_account(account.id)