from odoo import models, fields, api
from producteca.products.products import Product
from producteca.config.config import ConfigProducteca
from producteca.sales_orders.search_sale_orders import SearchSalesOrder, SearchSalesOrderParams
from producteca.sales_orders.sales_orders import SaleOrder
from producteca.shipments.shipment import Shipment
from producteca.payments.payments import Payment
import logging
import json
from datetime import datetime, timedelta
from odoo.addons.base.models.res_users import Command
from urllib.parse import quote
from odoo.tools.safe_eval import safe_eval
_logger = logging.getLogger(__name__)

class ProductecaQueue(models.Model):
    # Deprecated we use OCA Queue
    _name = "producteca.queue"
    _description = "Producteca Queue"

    active = fields.Boolean(string="Active", default=True)
    producteca_account_id = fields.Many2one(
        "producteca.account", string="Producteca Account"
    )
    producteca_body = fields.Text(string="Producteca Body")
    producteca_method = fields.Selection(
        [("create", "Create"),("update", "Update"), ("get", "Get"), ("post", "Post"), ("put", "Put"), ("delete", "Delete"), ("odoo_create", "Odoo Create")],
        string="Producteca Method",
    )
    model = fields.Char(string="Model")
    producteca_response = fields.Text(string="Producteca Response")
    odoo_item_id = fields.Integer(string="Odoo Item ID", readonly=True)
    response_status = fields.Char(string="Producteca Response Status")
    internal_process_error_msg = fields.Text(string="Internal Process Error Message")
