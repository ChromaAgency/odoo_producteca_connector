from odoo import models, fields
from odoo.exceptions import UserError
from producteca.config.config import ConfigProducteca
from producteca.sales_orders.sales_orders import SaleOrder


class ProductecaSaleordersWizard(models.TransientModel):
    _name = 'producteca.saleorders.wizard'
    _description = 'Wizard para obtener ordenes de venta de Producteca'

    producteca_account_id = fields.Many2one(
        'producteca.account',
        string='Cuenta de Producteca',
        required=True
    )
    search_text = fields.Char(
        string='Texto de búsqueda',
        required=True
    )

    def action_obtain_saleorders(self):
        producteca_products_ids = self.search_text.split(",")
        account = self.producteca_account_id
        client = account.get_client()
        for producteca_sale_order_id in producteca_products_ids:
            sale_order = client.SaleOrder.get(producteca_sale_order_id)
            if sale_order:
                self.env['sale.order'].with_delay()._upset_saleorder_from_producteca(account, sale_order.to_dict())
