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
        sale_orders = self.env['sale.order'].sudo().search([('producteca_id', 'in', producteca_products_ids), ('invoice_ids', '!=', False)])
        sale_orders_id = [sale_order.producteca_id for sale_order in sale_orders]
        sale_orders_to_create = [producteca_id for producteca_id in producteca_products_ids if producteca_id not in sale_orders_id]
        config = ConfigProducteca(
            token=self.producteca_account_id.bearer_token,
            api_key=self.producteca_account_id.api_key
        )
        if sale_orders_id:
            sale_orders_to_update = []
            for sale_order_id in sale_orders_id:
                sale_order = SaleOrder.get(config, sale_order_id)
                if sale_order:
                    sale_orders_to_update.append({
                        'producteca_id': sale_order_id,
                        'producteca_body': sale_order.model_dump_json(exclude_none=True),
                        'producteca_method': 'update',
                        'model': 'sale.order',
                        'producteca_account_id': self.producteca_account_id.id,
                        'odoo_item_id': sale_order_id
                        })
            self.env['producteca.queue'].sudo().create(sale_orders_to_update)
        for producteca_sale_order in sale_orders_to_create:
            sale_order = SaleOrder.get(config, producteca_sale_order)
            if sale_order:
                sale_orders_to_create.append({
                    'producteca_id': producteca_sale_order,
                    'producteca_body': sale_order.model_dump_json(exclude_none=True),
                    'producteca_method': 'create',
                    'model': 'sale.order',
                    'producteca_account_id': self.producteca_account_id.id})
        self.env['producteca.queue'].sudo().create(sale_orders_to_create)