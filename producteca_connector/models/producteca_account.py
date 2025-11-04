from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from producteca import ProductecaClient
import logging

_logger = logging.getLogger(__name__)


class ProductecaAccountConfig(models.Model):
    _name = 'producteca.account'
    _description = 'Producteca Account'
    _rec_name = 'account_name'

    active = fields.Boolean(string='Active', default=True)
    account_name = fields.Char(string='Account Name', required=True)
    api_key = fields.Char(string='API Key', required=True)
    bearer_token = fields.Char(string='Bearer Token', required=True)
    producteca_company_id = fields.Char(string='Producteca ID')

    company_id = fields.Many2one('res.company', string='Company')
    imported_sale_action = fields.Selection([
        ("quotation", "Create the sale order confirmed"),
        ("draft_invoice", "Confirm the sale order and create draft invoice"),
        ("confirm", "Confirm the sale order and create confirmed invoice"),
    ], string="Imported Sale Action", required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouse Location')
    default_warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse', required=True)

    pricelist_ids = fields.Many2many('product.pricelist', string='Pricelists to Sync in Producteca')
    is_stock_modified_by_producteca = fields.Boolean(string='Is Stock Modified by Producteca?')
    is_product_price_modified_by_producteca = fields.Boolean(string='Is Product Price Modified by Producteca?')
    is_producteca_able_to_create_products = fields.Boolean(string='Is Producteca Able to Create Products?')
    is_producteca_able_to_modified_products = fields.Boolean(string='Is Producteca Able to Modify Products?')
    create_if_dosnt_exist = fields.Boolean(string='Create If The Product Dosnt Exists')
    get_orders_from_last_days = fields.Integer(string='Get Orders From Last Days', default=7)
    is_odoo_able_to_update_producteca_prices = fields.Boolean(string='Is Odoo Able to Update Producteca Prices?')

    _sql_constraints = [
        ('check_price_sync_exclusivity', 
         'CHECK(NOT(is_product_price_modified_by_producteca = true AND is_odoo_able_to_update_producteca_prices = true))',
         'Only one price synchronization option can be active at a time. Either Producteca modifies product prices OR Odoo updates Producteca prices, but not both.')
    ]

    @api.constrains('pricelist_ids')
    def _check_default_pricelist(self):
        """Verifica que la primera pricelist tenga 'Default' como producteca_pricelist_name"""
        for record in self:
            if record.pricelist_ids:
                first_pricelist = record.pricelist_ids.sorted('id')[0]
                if not first_pricelist.producteca_pricelist_name or first_pricelist.producteca_pricelist_name != 'Default':
                    raise ValidationError(
                        _("The first pricelist must have 'Default' as Producteca Pricelist Name. "
                          "Please set the Producteca Pricelist Name to 'Default' for: %s") % first_pricelist.name
                    )

    def get_client(self):
        return ProductecaClient(api_key=self.api_key, token=self.bearer_token)

    def sync_all_products_from_producteca(self):
        """Sincroniza todos los productos de Producteca para esta cuenta"""
        self.ensure_one()
        return self.env['product.product'].sync_all_products_from_producteca()
