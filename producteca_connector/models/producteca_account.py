from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from producteca import ProductecaClient
import logging

_logger = logging.getLogger(__name__)


class ProductecaAccountConfig(models.Model):
    """Configuration model for Producteca accounts integration.
    
    This model manages the configuration and authentication details for connecting
    Odoo with Producteca marketplace. It handles API keys, synchronization settings,
    and business rules for data exchange between the two systems.
    
    Business Logic:
    - Each account represents a connection to a specific Producteca marketplace account
    - Provides authentication credentials and connection parameters
    - Defines synchronization behavior for products, prices, and stock
    - Manages warehouse mapping and order processing workflows
    - Enforces data consistency rules through constraints
    
    Key Features:
    - API authentication management
    - Bidirectional synchronization control
    - Warehouse and company mapping
    - Price synchronization rules
    - Product creation and modification permissions
    """
    _name = 'producteca.account'
    _description = 'Producteca Account Configuration'
    _rec_name = 'account_name'

    active = fields.Boolean(
        string='Active', 
        default=True,
        help="Indicates if this Producteca account configuration is active and available for synchronization."
    )
    account_name = fields.Char(
        string='Account Name', 
        required=True,
        help="Human-readable name for this Producteca account configuration."
    )
    api_key = fields.Char(
        string='API Key', 
        required=True,
        help="API key provided by Producteca for authentication. Keep this secure."
    )
    bearer_token = fields.Char(
        string='Bearer Token', 
        required=True,
        help="Bearer token for Producteca API authentication. Keep this secure."
    )
    producteca_company_id = fields.Char(
        string='Producteca Company ID',
        help="Unique identifier of the company in Producteca marketplace."
    )

    company_id = fields.Many2one(
        'res.company', 
        string='Company',
        help="Odoo company associated with this Producteca account."
    )
    warehouse_ids = fields.Many2many(
        'stock.warehouse', 
        string='Warehouse Locations',
        help="Warehouses that will be synchronized with this Producteca account."
    )
    default_warehouse_id = fields.Many2one(
        'stock.warehouse', 
        string='Default Warehouse', 
        required=True,
        domain="[('id', 'not in', warehouse_ids)]",
        help="Default warehouse used for stock operations when not specified."
    )

    imported_sale_action = fields.Selection([
        ("quotation", "Create the sale order confirmed"),
        ("draft_invoice", "Confirm the sale order and create draft invoice"),
        ("confirm", "Confirm the sale order and create confirmed invoice"),
    ], 
        string="Imported Sale Action", 
        required=True,
        help="Defines what action to take when importing sale orders from Producteca."
    )
    get_orders_from_last_days = fields.Integer(
        string='Get Orders From Last Days', 
        default=7,
        help="Number of days to look back when importing orders from Producteca."
    )

    pricelist_ids = fields.Many2many('product.pricelist', string='Pricelists to Sync in Producteca')
    default_pricelist_id = fields.Many2one(
        'product.pricelist', 
        string='Default Pricelist',
        domain="[('id', 'not in', pricelist_ids)]"
    )

    is_stock_modified_by_producteca = fields.Boolean(
        string='Is Stock Modified by Producteca?',
        help="If enabled, Producteca can modify stock levels in Odoo."
    )
    is_product_price_modified_by_producteca = fields.Boolean(
        string='Is Product Price Modified by Producteca?',
        help="If enabled, Producteca can modify product prices in Odoo."
    )
    is_producteca_able_to_create_products = fields.Boolean(
        string='Is Producteca Able to Create Products?',
        help="If enabled, Producteca can create new products in Odoo."
    )
    is_producteca_able_to_modified_products = fields.Boolean(
        string='Is Producteca Able to Modify Products?',
        help="If enabled, Producteca can modify existing product information in Odoo."
    )
    create_if_dosnt_exist = fields.Boolean(
        string='Create If The Product Doesn\'t Exist',
        help="If enabled, products will be created in Producteca if they don't exist when syncing from Odoo."
    )
    is_odoo_able_to_update_producteca_prices = fields.Boolean(
        string='Is Odoo Able to Update Producteca Prices?',
        help="If enabled, Odoo can update product prices in Producteca marketplace."
    )
    is_odoo_able_to_update_producteca_stock = fields.Boolean(
        string='Is Odoo Able to Update Producteca Stock?',
        help="If enabled, Odoo can update product stock quantities in Producteca marketplace."
    )

    is_odoo_able_to_update_producteca_shipments = fields.Boolean(
        string='Is Odoo Able to Update Producteca Shipments?',
        help="If enabled, Odoo can update shipment information in Producteca marketplace."
    )
    is_odoo_able_to_update_shipment_date = fields.Boolean(
        string='Is Odoo Able to Update Shipment Date?',
        help="If enabled, Odoo can update the shipment date in Producteca marketplace."
    )


    _sql_constraints = [
        ('check_price_sync_exclusivity', 
         'CHECK(NOT(is_product_price_modified_by_producteca = true AND is_odoo_able_to_update_producteca_prices = true))',
         'Only one price synchronization option can be active at a time. Either Producteca modifies product prices OR Odoo updates Producteca prices, but not both.')
    ]

    @api.constrains('is_odoo_able_to_update_producteca_shipments', 'is_odoo_able_to_update_shipment_date')
    def _check_shipment_date_requires_shipment_update(self):
        """Validate that shipment date update requires shipment update to be enabled."""
        for record in self:
            if record.is_odoo_able_to_update_shipment_date and not record.is_odoo_able_to_update_producteca_shipments:
                raise ValidationError(
                    _("To enable 'Is Odoo Able to Update Shipment Date', you must first enable "
                      "'Is Odoo Able to Update Producteca Shipments'.")
                )

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

    @api.constrains('default_warehouse_id', 'warehouse_ids')
    def _check_default_warehouse_restrictions(self):
        for record in self:
            if record.default_warehouse_id and record.default_warehouse_id in record.warehouse_ids:
                raise ValidationError(
                    _("The default warehouse '%s' cannot be included in the additional warehouses. "
                      "Please remove it from the additional warehouses or select a different default warehouse.") 
                    % record.default_warehouse_id.name
                )
            for warehouse in record.warehouse_ids:
                if not warehouse.producteca_warehouse_name:
                    raise ValidationError(
                        _("Additional warehouse '%s' must have a Producteca Warehouse Name configured. "
                          "Please set the Producteca Warehouse Name for this warehouse.") 
                        % warehouse.name
                    )

    @api.onchange('default_pricelist_id')
    def _onchange_default_pricelist_id(self):
        if self.default_pricelist_id and self.default_pricelist_id in self.pricelist_ids:
            self.pricelist_ids = [(3, self.default_pricelist_id.id)]

    @api.onchange('pricelist_ids')
    def _onchange_pricelist_ids(self):
        if self.default_pricelist_id and self.default_pricelist_id in self.pricelist_ids:
            self.default_pricelist_id = False

    @api.onchange('default_warehouse_id')
    def _onchange_default_warehouse_id(self):
        if self.default_warehouse_id and self.default_warehouse_id in self.warehouse_ids:
            self.warehouse_ids = [(3, self.default_warehouse_id.id)]

    @api.onchange('warehouse_ids')
    def _onchange_warehouse_ids(self):
        if self.default_warehouse_id and self.default_warehouse_id in self.warehouse_ids:
            self.default_warehouse_id = False

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

    def _toggle_product_creation_cron(self):
        """Activate or deactivate the product creation cron based on create_if_dosnt_exist.
        
        The cron is activated when at least one active account has create_if_dosnt_exist=True.
        The cron is deactivated when no active accounts have create_if_dosnt_exist=True.
        """
        cron = self.env.ref('producteca_connector.ir_cron_create_product_in_producteca_queue', raise_if_not_found=False)
        if not cron:
            return
        
        has_active_account = self.env['producteca.account'].sudo().search([
            ('active', '=', True),
            ('create_if_dosnt_exist', '=', True)
        ], limit=1)
        
        cron.sudo().write({'active': bool(has_active_account)})

    def get_client(self):
        """Get authenticated Producteca API client.
        
        Returns:
            ProductecaClient: Authenticated client instance for making API calls to Producteca.
            
        Raises:
            Exception: If authentication credentials are invalid or client creation fails.
        """
        return ProductecaClient(api_key=self.api_key, token=self.bearer_token)

    def sync_all_products_from_producteca(self):
        """Synchronize all products from Producteca marketplace to Odoo.
        
        This method triggers a full synchronization of products from the connected
        Producteca marketplace account to the current Odoo database. It respects
        the configuration settings for product creation and modification permissions.
        
        Returns:
            dict: Result of the synchronization operation, typically including
                  counts of created, updated, and skipped products.
                  
        Note:
            This operation can be time-consuming for large product catalogs.
            Consider running in background for large datasets.
        """
        self.ensure_one()
        return self.env['product.template'].sync_all_products_from_producteca()


    def write(self, vals):
        result = super(ProductecaAccountConfig, self).write(vals)
        if 'create_if_dosnt_exist' in vals or 'active' in vals:
            self._toggle_product_creation_cron()
        return result

    def unlink(self):
        result = super(ProductecaAccountConfig, self).unlink()
        self.env['producteca.account']._toggle_product_creation_cron()
        return result

    def sync_all_stock_to_producteca(self):
        """Synchronize all product stock from Odoo to Producteca marketplace.
        
        This method synchronizes stock quantities for all active product connections
        in this Producteca account. It processes each warehouse configured in the account
        and sends current stock levels to Producteca marketplace.
        
        Business Logic:
        - Only syncs if 'is_odoo_able_to_update_producteca_stock' is enabled
        - Processes all active connections (producteca.product.connections)
        - Sends stock for each configured warehouse
        - Respects 'create_if_dosnt_exist' setting for products
        - Uses queued jobs for better performance
        
        Returns:
            dict: Action result with success message
            
        Raises:
            ValidationError: If stock sync is not enabled for this account
        """
        self.ensure_one()
        
        if not self.is_odoo_able_to_update_producteca_stock:
            raise ValidationError(
                _("Stock synchronization to Producteca is not enabled for account '%s'. "
                  "Please enable 'Is Odoo Able to Update Producteca Stock' in the account settings.") 
                % self.account_name
            )
        connections = self.env['producteca.product.connections'].search([
            ('producteca_account_id', '=', self.id),
            ('active', '=', True)
        ])
        
        if not connections:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Products Found'),
                    'message': _('No active product connections found for this Producteca account.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        synced_count = 0
        stock_quant_obj = self.env['stock.quant']
        
        for connection in connections:
            stock_quant_obj.with_delay().sync_product_stock_to_producteca(connection.id)
            synced_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Stock Sync Queued'),
                'message': _('%d products queued for stock synchronization to Producteca.') % synced_count,
                'type': 'success',
                'sticky': False,
            }
        }
