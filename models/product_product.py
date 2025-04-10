from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        
        for product in products:
            producteca_account = self.env['producteca.account'].search([
                ('company_id', '=', product.company_id.id),
                ('is_producteca_able_to_create_products', '=', True)
            ], limit=1)
            
            if producteca_account:
                self.env['producteca.queue'].create_product_in_producteca(product, producteca_account)
        
        return products