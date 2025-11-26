from odoo import fields,models, Command
from odoo.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'
   
    producteca_payment_state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
    ], string='Estado del pago', default='pending')
    # TODO: Couldnt this be gotten from the order directly
    producteca_order_id = fields.Char(string='ID de la orden de producteca')
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')
    producteca_payment_data = fields.Text(string='Datos del pago de producteca')

    def add_invoice_to_producteca(self):
        if self.move_type == 'out_invoice' and self.producteca_account_id and self.producteca_order_id:
            client = self.producteca_account_id.get_client()
            if not self.access_token:
                self._portal_ensure_token()   
            invoice_dict = {
                    "id": int(self.producteca_order_id),
                    "invoiceIntegration": {
                        "documentUrl": f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/facturas/{self.id}/{self.access_token}/factura_producteca.pdf",
                        "app": 232,
                        "integrationId": "151",
                        "decreaseStock": True
                        }
                    }
            result = client.SalesOrder(**invoice_dict).invoice_integration()
    
    def _create_payments_from_producteca(self):
        self.ensure_one()
        
        if not self.producteca_payment_data:
            return
            
        journals = self.env['account.journal'].search([('producteca_payment_method', '!=', False)])
        
        payments = safe_eval(self.producteca_payment_data)
            
        for payment in payments:
            # ! Are there any other status?
            if payment['status'] == 'Approved':
                self = self.with_context(update_from_invoice=True)
                matching_journals = journals.filtered(lambda journal: journal.producteca_payment_method == payment['method'])
                
                if not matching_journals:
                    raise ValidationError(f"[PRODUCTECA] No se encontró el diario de pago para el método '{payment['method']}'")
                    
                journal_id = matching_journals[0]
                
                payment_register = self.env['account.payment.register'].with_context(
                    active_model='account.move',
                    active_ids=self.ids,
                ).create({
                    'amount': payment['amount'],
                    'payment_date': payment['date'],
                    'journal_id': journal_id.id,
                })
                
                payment_result = payment_register.action_create_payments()
                    
                if payment_result and 'res_id' in payment_result:
                    created_payment = self.env['account.payment'].browse(payment_result['res_id'])
                    created_payment.write({
                        'producteca_payment_id': str(payment['id']),
                        'producteca_account_id': self.producteca_account_id.id,
                    })
                    created_payment.action_post()
                
                self.producteca_payment_state = 'approved'

    def action_post(self):
        result = super(AccountMove, self).action_post()
        for move in self:
            move.with_delay().add_invoice_to_producteca()
            move.with_delay()._create_payments_from_producteca()
        return result
