from odoo import models, fields
from odoo.exceptions import UserError


class ProductSubmissionRejectWizard(models.TransientModel):
    """Admin rejects a designer product submission with a reason."""
    _name        = 'product.submission.reject.wizard'
    _description = 'Reject Product Submission'

    submission_id     = fields.Many2one('product.submission', string='Submission', required=True)
    rejection_reason  = fields.Text(string='Reason for Rejection', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        rec = self.submission_id
        if rec.state != 'submitted':
            raise UserError('Submission is no longer in Submitted state.')
        rec.write({
            'state':            'rejected',
            'rejection_reason': self.rejection_reason,
            'reviewed_by':      self.env.uid,
        })
        rec.message_post(
            body=f'<b>Rejected:</b> {self.rejection_reason}',
            subject='Product Submission Rejected',
        )
        return {'type': 'ir.actions.act_window_close'}
