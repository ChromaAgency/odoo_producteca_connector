from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    producteca_warehouse_name = fields.Char(string='Producteca Warehouse Name')

    @api.constrains('producteca_warehouse_name')
    def _check_producteca_name_not_default(self):
        """No permitir 'Default' como nombre de warehouse, se maneja automáticamente"""
        for record in self:
            if record.producteca_warehouse_name and record.producteca_warehouse_name.lower() == 'default':
                raise ValidationError(
                    _("Cannot use 'Default' as Producteca Warehouse Name. "
                      "The default warehouse is handled automatically by the system.")
                )

    def _get_producteca_warehouse_name(self, account):
        """Obtiene el nombre correcto para el warehouse en producteca"""
        if account.default_warehouse_id and self.id == account.default_warehouse_id.id:
            return "Default"
        return self.producteca_warehouse_name