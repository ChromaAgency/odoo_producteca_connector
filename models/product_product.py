from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_producteca_product = fields.Boolean(string="Is Producteca Product", related='product_tmpl_id.is_producteca_product', store=True)
    is_already_sync = fields.Boolean(string="Is Already Sync", readonly=True)
