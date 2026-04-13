from odoo import models, fields, api
from datetime import date, timedelta

class PosConfig(models.Model):
    _inherit = 'pos.config'

    # Consignment overall metrics to display in Kanban
    consignment_draft_settlements = fields.Integer(compute='_compute_consignment_metrics')
    consignment_pending_amount = fields.Float(compute='_compute_consignment_metrics')
    consignment_low_stock = fields.Integer(compute='_compute_consignment_metrics')
    consignment_active_designers = fields.Integer(compute='_compute_consignment_metrics')

    def _compute_consignment_metrics(self):
        # Calculate once to save DB trips, then assign to all records
        Settlement = self.env['settlement.record'].sudo()
        Product = self.env['product.template'].sudo()
        
        draft_count = Settlement.search_count([('state', '=', 'draft')])
        posted = Settlement.search([('state', '=', 'posted')])
        pending_amt = sum(p.payout_amount for p in posted)
        
        all_consignment = Product.search([
            ('is_consignment', '=', True),
            ('active', '=', True),
        ])
        low_stock = sum(1 for p in all_consignment if p.qty_available <= p.low_stock_threshold)
        
        ninety_days_ago = date.today() - timedelta(days=90)
        active_designers = len(Settlement.search([
            ('period_start', '>=', ninety_days_ago)
        ]).mapped('designer_id'))

        for config in self:
            config.consignment_draft_settlements = draft_count
            config.consignment_pending_amount = pending_amt
            config.consignment_low_stock = low_stock
            config.consignment_active_designers = active_designers
