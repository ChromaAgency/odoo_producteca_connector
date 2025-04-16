from odoo import models, fields, api

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    producteca_warehouse_name = fields.Char(string='Producteca Warehouse Name')