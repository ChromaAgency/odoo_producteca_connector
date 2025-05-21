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
                        payment_vals = {
                            'date': payment['date'],
                            'amount': payment['amount'],
                            'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'journal_id': journal_id.id,
                            'currency_id': move.currency_id.id,
                            'partner_id': move.partner_id.id,
                            'reconciled_invoice_ids': [Command.set([move.id])], #TODO ver en account payments group o en mercadopago en silfab (prioridad esto ultimo)
                            'producteca_payment_id': payment['id']
                        }
                        _logger.info('move %s',move.id)
                        _logger.info('Payment vals %s',payment_vals)
                        payment = self.env['account.payment'].create(payment_vals)
                        payment.action_validate()
                        move.producteca_payment_state = 'approved'
        return result

    # def _post(self, soft=True):
    #     res = super(AccountMove, self)._post(soft)
    #     for move in self:
    #         if move.invoice_line_ids.sale_line_ids.order_id[:1].is_third_party_imported and move.move_type == 'out_invoice':
    #             journal_id =  self.env['ir.config_parameter'].sudo().get_param('third_party_importers.third_party_account_journal_id') or False
    #             if not journal_id:
    #                 raise UserError(_('Please configure the journal for third party importers in settings'))
    #             payment_register = self.env['account.payment.register'].with_context(
    #                 active_model='account.move',
    #                 active_ids=move.ids,
    #             ).create({
    #                 'amount': move.amount_residual,
    #                 'payment_date': move.invoice_date,
    #                 'journal_id': int(journal_id),
    #             })
    #             payment_register.action_create_payments()