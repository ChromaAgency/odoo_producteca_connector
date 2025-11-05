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
    default_pricelist_id = fields.Many2one(
        'product.pricelist', 
        string='Default Pricelist',
        domain="[('id', 'not in', pricelist_ids)]"
    )
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

    @api.constrains('default_pricelist_id', 'pricelist_ids')
    def _check_default_pricelist_restrictions(self):
        for record in self:
            if record.default_pricelist_id and record.default_pricelist_id in record.pricelist_ids:
                raise ValidationError(
                    _("The default pricelist '%s' cannot be included in the additional pricelists. "
                      "Please remove it from the additional pricelists or select a different default pricelist.") 
                    % record.default_pricelist_id.name
                )
            for pricelist in record.pricelist_ids:
                if not pricelist.producteca_pricelist_name:
                    raise ValidationError(
                        _("Additional pricelist '%s' must have a Producteca Pricelist Name configured. "
                          "Please set the Producteca Pricelist Name for this pricelist.") 
                        % pricelist.name
                    )

    @api.onchange('default_pricelist_id')
    def _onchange_default_pricelist_id(self):
        if self.default_pricelist_id and self.default_pricelist_id in self.pricelist_ids:
            self.pricelist_ids = [(3, self.default_pricelist_id.id)]

    @api.onchange('pricelist_ids')
    def _onchange_pricelist_ids(self):
        if self.default_pricelist_id and self.default_pricelist_id in self.pricelist_ids:
            self.default_pricelist_id = False

    @api.onchange('is_odoo_able_to_update_producteca_prices', 'default_pricelist_id')
    def _onchange_price_sync_warning(self):
        """Warning cuando se activa sync de precios sin lista por defecto"""
        if self.is_odoo_able_to_update_producteca_prices and not self.default_pricelist_id:
            return {
                'warning': {
                    'title': _('Price Synchronization Warning'),
                    'message': _('You have enabled "Is Odoo Able to Update Producteca Prices" but no Default Pricelist is configured. '
                               'The product list price will be sent as the default price to Producteca. '
                               'Consider setting a Default Pricelist for better price control.')
                }
            }

    def get_client(self):
        return ProductecaClient(api_key=self.api_key, token=self.bearer_token)

    def sync_all_products_from_producteca(self):
        self.ensure_one()
        return self.env['product.product'].sync_all_products_from_producteca()
