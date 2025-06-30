from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_producteca_product = fields.Boolean(string="Is Producteca Product")

    def _update_product_price(self):
        # TODO: Check why 3 queues are getting generated
        producteca_connection = self.env['producteca.connections'].sudo().search([('product_id', '=', self.id)])
        client = producteca_connection.producteca_account_id.get_client()
        body_dict = {
            "code": str(producteca_connection.product_id.id),
            "prices": [{"amount": self.list_price, "currency": producteca_connection.product_id.currency_id.name, "priceList": "Default"}]
        }
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = producteca_connection.producteca_account_id.create_if_dosnt_exist
        product_service.synchronize(body_dict)

    def write(self, vals):
        _ = super().write(vals)
        for rec in self:
            if rec.is_producteca_product and 'list_price' in vals:
                rec.with_delay()._update_product_price()
        return _
