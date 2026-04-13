from odoo import models, fields, api
from odoo.exceptions import UserError


class SettlementDisputeWizard(models.TransientModel):
    """
    Designer (or admin on behalf) raises a dispute on a posted settlement.
    Requires a reason before flagging — prevents empty disputes.
    """
    _name        = 'settlement.dispute.wizard'
    _description = 'Raise Settlement Dispute'

    settlement_id  = fields.Many2one('settlement.record', string='Settlement', required=True)
    dispute_reason = fields.Text(string='Reason for Dispute', required=True,
        help='Explain clearly what figures you believe are incorrect.')

    def action_confirm_dispute(self):
        self.ensure_one()
        if not self.dispute_reason or not self.dispute_reason.strip():
            raise UserError('Please provide a reason before raising a dispute.')
        rec = self.settlement_id
        rec.write({
            'state':          'disputed',
            'dispute_reason': self.dispute_reason,
            'dispute_date':   fields.Datetime.now(),
        })
        rec.message_post(
            body=f'<b>Dispute raised:</b> {self.dispute_reason}',
            subject='Settlement Disputed',
        )
        return {'type': 'ir.actions.act_window_close'}


class SettlementDisputeResolveWizard(models.TransientModel):
    """
    Admin resolves a disputed settlement, optionally recalculates,
    then moves back to posted state.
    """
    _name        = 'settlement.dispute.resolve.wizard'
    _description = 'Resolve Settlement Dispute'

    settlement_id      = fields.Many2one('settlement.record', string='Settlement', required=True)
    dispute_response   = fields.Text(string='Resolution Note', required=True,
        help='Explain what was checked and what the outcome is.')
    recalculate        = fields.Boolean(string='Recalculate Settlement Before Resolving',
        default=False, help='Tick to re-aggregate POS + online sales before resolving.')

    def action_resolve(self):
        self.ensure_one()
        rec = self.settlement_id
        if rec.state != 'disputed':
            raise UserError('Settlement is no longer in Disputed state.')
        if self.recalculate:
            rec.action_recalculate()
        rec.write({
            'state':               'posted',
            'dispute_response':    self.dispute_response,
            'dispute_resolved_by': self.env.uid,
        })
        rec.message_post(
            body=f'<b>Dispute resolved:</b> {self.dispute_response}',
            subject='Dispute Resolved — Settlement Reinstated',
        )
        return {'type': 'ir.actions.act_window_close'}
