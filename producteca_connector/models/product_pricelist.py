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
        for record in self:
            if record.producteca_pricelist_name and record.producteca_pricelist_name.lower() == 'default':
                raise ValidationError(
                    _("Cannot use 'Default' as Producteca Pricelist Name. "
                      "The default pricelist is handled automatically by the system.")
                )

    def _get_producteca_pricelist_name(self, account):
        if account.default_pricelist_id and self.id == account.default_pricelist_id.id:
            return "Default"
        return self.producteca_pricelist_name



    def _sync_single_product_price(self, account_data, sync_data):
        
        client = ProductecaClient(api_key=account_data['api_key'], token=account_data['bearer_token'])
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account_data['create_if_dosnt_exist']
        
        result = product_service.synchronize(sync_data)
        return result

    def _sync_prices_for_account(self, account_id, pricelist_id=None, use_list_price=False):
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
            product = connection.product_id
            
            if not product or not product.default_code:
                continue
            
            if use_list_price:
                if product.product_tmpl_id.list_price:
                    sync_data = {
                        'sku': product.default_code,
                        'prices': [{
                            'amount': product.product_tmpl_id.list_price,
                            'currency': "Usd" if account.company_id.currency_id.id == self.env.ref('base.USD').id else "Local",
                            'priceList': 'Default'
                        }]
                    }
                    self.with_delay()._sync_single_product_price(account_data, sync_data)
            else:
                pricelist = self.env['product.pricelist'].browse(pricelist_id)
                pricelist_name = pricelist._get_producteca_pricelist_name(account)
                
                if not pricelist_name:
                    _logger.warning(f"Pricelist {pricelist.name} (ID: {pricelist.id}) no tiene producteca_pricelist_name configurado. Saltando sincronización.")
                    continue
                    
                price = pricelist._get_product_price(product, 1)
                if price:
                    sync_data = {
                        'sku': product.default_code,
                        'prices': [{
                            'amount': price,
                            'currency': "Usd" if pricelist.currency_id.id == self.env.ref('base.USD').id else "Local",
                            'priceList': pricelist_name
                        }]
                    }
                    self.with_delay()._sync_single_product_price(account_data, sync_data)

    def _sync_single_product_for_account(self, product_id, account_id, pricelist_id=None, use_list_price=False):
        account = self.env['producteca.account'].browse(account_id)
        product = self.env['product.product'].browse(product_id)
        
        if not product.exists() or not product.default_code:
            return
        
        account_data = {
            'api_key': account.api_key,
            'bearer_token': account.bearer_token,
            'create_if_dosnt_exist': account.create_if_dosnt_exist
        }
        
        if use_list_price:
            if product.product_tmpl_id.list_price:
                sync_data = {
                    'sku': product.default_code,
                    'prices': [{
                        'amount': product.product_tmpl_id.list_price,
                        'currency': "Usd" if account.company_id.currency_id.id == self.env.ref('base.USD').id else "Local",
                        'priceList': 'Default'
                    }]
                }
                self.with_delay()._sync_single_product_price(account_data, sync_data)
        else:
            pricelist = self.env['product.pricelist'].browse(pricelist_id)
            pricelist_name = pricelist._get_producteca_pricelist_name(account)
            
            if not pricelist_name:
                return
                
            price = pricelist._get_product_price(product, 1)
            if price:
                sync_data = {
                    'sku': product.default_code,
                    'prices': [{
                        'amount': price,
                        'currency': "Usd" if pricelist.currency_id.id == self.env.ref('base.USD').id else "Local",
                        'priceList': pricelist_name
                    }]
                }
                self.with_delay()._sync_single_product_price(account_data, sync_data)

    def _sync_product_price_on_change(self, product_id, specific_pricelist_id=None):
        product = self.env['product.product'].browse(product_id)
        
        if not product.exists() or not product.default_code:
            return
        
        connections = self.env['producteca.product.connections'].search([
            ('product_id', '=', product.id)
        ])
        
        if not connections:
            return
        
        if specific_pricelist_id:
            producteca_accounts = self.env['producteca.account'].search([
                '|',
                ('default_pricelist_id', '=', specific_pricelist_id),
                ('pricelist_ids', 'in', [specific_pricelist_id]),
                ('active', '=', True),
                ('is_odoo_able_to_update_producteca_prices', '=', True)
            ])
        else:
            producteca_accounts = self.env['producteca.account'].search([
                ('active', '=', True),
                ('is_odoo_able_to_update_producteca_prices', '=', True)
            ])
        
        for account in producteca_accounts:
            if account.id not in connections.mapped('producteca_account_id').ids:
                continue
            
            if specific_pricelist_id:
                self._sync_single_product_for_account(product.id, account.id, specific_pricelist_id)
            else:
                if account.default_pricelist_id:
                    self._sync_single_product_for_account(product.id, account.id, account.default_pricelist_id.id)
                else:
                    self._sync_single_product_for_account(product.id, account.id, use_list_price=True)
                
                for pricelist in account.pricelist_ids:
                    if pricelist.producteca_pricelist_name:
                        self._sync_single_product_for_account(product.id, account.id, pricelist.id)

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

    def write(self, vals):
        pricelists_to_sync = []
        if 'currency_id' in vals:
            for pricelist in self:
                if self._is_pricelist_in_producteca_account(pricelist):
                    pricelists_to_sync.append(pricelist.id)
            if pricelists_to_sync:
                self.with_delay()._trigger_pricelist_config_sync(pricelists_to_sync)
        
        result = super(ProductPricelist, self).write(vals)        
        
        return result

    def _is_pricelist_in_producteca_account(self, pricelist):
        accounts = self.env['producteca.account'].search([
            '|',
            ('default_pricelist_id', '=', pricelist.id),
            ('pricelist_ids', 'in', [pricelist.id]),
            ('active', '=', True),
            ('is_odoo_able_to_update_producteca_prices', '=', True)
        ])
        return bool(accounts)

    def _trigger_pricelist_config_sync(self, pricelist_ids):
        for pricelist_id in pricelist_ids:
            connections = self.env['producteca.product.connections'].search([])
            
            for connection in connections:
                product = connection.product_id
                if product and product.exists():
                    self.with_delay()._sync_product_price_on_change(product.id, pricelist_id)