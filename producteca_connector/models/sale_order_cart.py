from odoo import models, fields, api


class SaleOrderCart(models.Model):
    _name = "sale.order.cart"
    _description = "Sale Order Cart"
    _rec_name = "producteca_id"

    producteca_id = fields.Char(string="Producteca ID")
    order_ids = fields.One2many("sale.order", "cart_id", string="Orders")


