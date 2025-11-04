from odoo import models, fields, api
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
import requests

class ProductecaConnections(models.Model):
    _name = 'producteca.product.connections'
    _description = 'Producteca Connections'
    
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    producteca_variation_id = fields.Char(string='Producteca Variation ID')
    producteca_id = fields.Char(string='Producteca ID', required=True)
    active = fields.Boolean(string='Active', default=True)


    def _sync_description_product(self, account_data, product_dict):
        """Método que se ejecuta en la cola para sincronizar la descripción de un producto"""        
        headers = {
            "Authorization": f"Bearer {account_data['bearer_token']}",
            "x-api-key": account_data['api_key'],
            "Content-Type": "application/json",
            "createifitdoesntexist": str(account_data['create_if_dosnt_exist']).lower()
        }
        _logger.info(f"product dict to sync description: {product_dict}")
        #result = requests.post("https://api-external.producteca.com/products/synchronize", headers=headers, json=product_dict)
        #_logger.info(f"Sync description result: {result}")
    
    def fix_producteca_descriptions(self):
        connections = self.env['producteca.product.connections'].sudo().search([])
        for connection in connections:
            product = connection.product_id
            account = connection.producteca_account_id
            if not product.description:
                continue
            
            # Solo convertir Markup a string, manteniendo el HTML
            description_text = str(product.description)
            
            account_data = {
                'api_key': account.api_key,
                'bearer_token': account.bearer_token,
                'create_if_dosnt_exist': account.create_if_dosnt_exist
            }
            product_dict = {
                "sku": product.default_code,
                "notes": description_text
            }

            self.with_delay()._sync_description_product(account_data, product_dict)
        return True