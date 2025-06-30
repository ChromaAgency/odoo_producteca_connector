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
    # TODO: Couldnt this be gotten from the order directly
    producteca_order_id = fields.Char(string='ID de la orden de producteca')
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')
    producteca_invoice_already_exists = fields.Boolean(string='Factura de producteca ya existe')
    producteca_payment_data = fields.Text(string='Datos del pago de producteca')

    def add_invoice_to_producteca(self):
        # I Think we dont need this anymore, this was used when producteca_invoice_already_exists was False, is it really necessary?
        # response = SaleOrder.synchronize(SaleOrder(**producteca_body))
        client = self.producteca_account_id.get_client()
        if not self.access_token:
            self._portal_ensure_token()   
        invoice_dict = {
                "id": int(self.producteca_order_id),
                "invoiceIntegration": {
                    "documentUrl": f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/facturas/{self.id}/{self.access_token}/factura_producteca.pdf",
                    "integrationId": str(self.name) if self.name else str(self.id),
                    }
                }
        client.SalesOrder(**invoice_dict).invoice_integration()
    
    def _create_payments_from_producteca(self):
        self.ensure_one()
        journals = self.env['account.journal'].search([])
        if self.producteca_payment_data:
            payments = safe_eval(self.producteca_payment_data)
            # ! Why index 0?
            for payment in payments[0]:
                # ! Are there any other status?
                if payment['status'] == 'Approved':
                    self = self.with_context(update_from_invoice=True)
                    journal_id = journals.filtered(lambda journal: journal.producteca_payment_method == payment['method'])[0] if journals.filtered(lambda journal: journal.producteca_payment_method == payment['method']) else False
                    if not journal_id:
                        _logger.info('No se encontro el diario de pago de producteca')
                        continue
                    payment_register = self.env['account.payment.register'].with_context(
                        active_model='account.move',
                        active_ids=self.ids,
                    ).create({
                        'amount': payment['amount'],
                        'payment_date': payment['date'],
                        'journal_id': journal_id.id,
                    })
                    payment_register.action_create_payments()
                    # TODO: This should be part of the wizard
                    self.matched_payment_ids.sorted('create_date', reverse=True)[:1].write({'producteca_payment_id': payment['id']})
                    self.producteca_payment_state = 'approved'

    def action_post(self):
        result = super(AccountMove, self).action_post()
        for move in self:
            move.with_delay().add_invoice_to_producteca()
            move._create_payments_from_producteca()
        return result
