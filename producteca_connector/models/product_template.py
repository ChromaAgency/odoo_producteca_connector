from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_producteca_product = fields.Boolean(string="Is Producteca Product", compute="_compute_is_producteca_product", store=True)

    @api.depends('product_variant_ids.is_producteca_product')
    def _compute_is_producteca_product(self):
        for template in self:
            template.is_producteca_product = any(variant.is_producteca_product for variant in template.product_variant_ids)