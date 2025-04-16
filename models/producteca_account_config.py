from odoo import models, fields, api
from odoo.tools.translate import _

class ProductecaAccountConfig(models.Model):
    _name = 'producteca.account'
    _description = 'Producteca Account'
    _rec_name = 'account_name'

    active= fields.Boolean(string='Active', default=True)
    account_name = fields.Char(string='Account Name', required=True)
    api_key = fields.Char(string='API Key')
    bearer_token = fields.Char(string='Bearer Token')

    company_id = fields.Many2one('res.company', string='Company')
    imported_sale_action = fields.Selection([
        ("quotation", "Create the sale order confirmed"),
        ("draft_invoice", "Confirm the sale order and create draft invoice"),
        ("confirm", "Confirm the sale order and create confirmed invoice"),
    ], string="Imported Sale Action")
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouse Location')

    pricelist_to_sync = fields.Many2one('product.pricelist', string='Pricelist to Sync in Producteca')
    is_stock_modified_by_producteca = fields.Boolean(string='Is Stock Modified by Producteca?')
    is_product_price_modified_by_producteca = fields.Boolean(string='Is Product Price Modified by Producteca?')
    is_producteca_able_to_create_products = fields.Boolean(string='Is Producteca Able to Create Products?')
    create_if_dosnt_exist = fields.Boolean(string='Create If The Product Dosnt Exists')