from odoo import fields,models, Command
from odoo.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
   
    producteca_payment_state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
    ], string='Estado del pago', default='pending')
    producteca_order_id = fields.Char(string='ID de la orden de producteca')
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')
    producteca_invoice_already_exists = fields.Boolean(string='Factura de producteca ya existe')
    producteca_payment_data = fields.Text(string='Datos del pago de producteca')

    def action_post(self):
        result = super(AccountMove, self).action_post()
        journals = self.env['account.journal'].search([])
        for move in self:
            if move.producteca_payment_data:
                payments = safe_eval(move.producteca_payment_data)
                for payment in payments[0]:
                    if payment['status'] == 'Approved':
                        self = self.with_context(update_from_invoice=True)
                        journal_id = journals.filtered(lambda journal: journal.producteca_payment_method == payment['method'])[0] if journals.filtered(lambda journal: journal.producteca_payment_method == payment['method']) else False
                        if not journal_id:
                            _logger.info('No se encontro el diario de pago de producteca')
                            continue
                        payment_register = self.env['account.payment.register'].with_context(
                            active_model='account.move',
                            active_ids=move.ids,
                        ).create({
                            'amount': payment['amount'],
                            'payment_date': payment['date'],
                            'journal_id': journal_id.id,
                        })
                        payment_register.action_create_payments()
                        move.matched_payment_ids.sorted('create_date', reverse=True)[:1].write({'producteca_payment_id': payment['id']})
                        move.producteca_payment_state = 'approved'
                        self.env['producteca.queue'].create({
                                'producteca_method': 'update' if move.producteca_invoice_already_exists else 'create',
                                'producteca_body': {"id": move.producteca_order_id, "invoiceIntegration":{"decreaseStock": True}},
                                'model':'account.move',
                                'producteca_account_id': move.producteca_account_id.id,
                            })
        return result