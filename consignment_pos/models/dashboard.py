from odoo import models, fields, api
from datetime import date, timedelta


class ConsignmentDashboard(models.Model):

    _name        = 'consignment.dashboard'
    _description = 'Consignment Dashboard'
    _rec_name    = 'name'

    name = fields.Char(default='Dashboard', readonly=True)

    # ── KPI fields (all computed, not stored) ────────────────────────────────
    total_draft_settlements   = fields.Integer(
        string='Pending Settlements',
        compute='_compute_kpis')
    total_posted_settlements  = fields.Integer(
        string='Awaiting Payment',
        compute='_compute_kpis')
    total_unpaid_amount       = fields.Float(
        string='Total Unpaid Payout',
        compute='_compute_kpis', digits=(16, 2))
    total_designers_active    = fields.Integer(
        string='Active Designers',
        compute='_compute_kpis')
    this_week_sales           = fields.Float(
        string='This Week Sales (All Channels)',
        compute='_compute_kpis', digits=(16, 2))
    this_week_payout          = fields.Float(
        string='This Week Payout Due',
        compute='_compute_kpis', digits=(16, 2))
    low_stock_products        = fields.Integer(
        string='Low Stock Products',
        compute='_compute_kpis')
    overdue_settlements       = fields.Integer(
        string='Overdue Settlements (>7 days posted)',
        compute='_compute_kpis')

    def _compute_kpis(self):
        for rec in self:
            Settlement = self.env['settlement.record']

            # Draft (pending approval)
            rec.total_draft_settlements = Settlement.search_count(
                [('state', '=', 'draft')])

            # Posted (approved but not paid)
            posted = Settlement.search([('state', '=', 'posted')])
            rec.total_posted_settlements = len(posted)
            rec.total_unpaid_amount = sum(p.payout_amount for p in posted)

            # Active designers (have at least one settlement in last 90 days)
            ninety_days_ago = date.today() - timedelta(days=90)
            rec.total_designers_active = len(Settlement.search([
                ('period_start', '>=', ninety_days_ago)
            ]).mapped('designer_id'))

            # This week
            today       = date.today()
            week_start  = today - timedelta(days=today.weekday())
            week_end    = week_start + timedelta(days=6)
            this_week   = Settlement.search([
                ('period_start', '>=', week_start),
                ('period_end',   '<=', week_end),
            ])
            rec.this_week_sales  = sum(s.total_sales  for s in this_week)
            rec.this_week_payout = sum(s.payout_amount for s in this_week)

            # Low stock products (qty_available <= per-product threshold)
            all_consignment = self.env['product.template'].search([
                ('is_consignment', '=', True),
                ('active', '=', True),
            ])
            rec.low_stock_products = sum(
                1 for p in all_consignment
                if p.qty_available <= p.low_stock_threshold
            )

            # Overdue: settlements posted but period ended more than 7 days ago
            overdue_date = fields.Date.today() - timedelta(days=7)
            rec.overdue_settlements = Settlement.search_count([
                ('state',      '=', 'posted'),
                ('period_end', '<=', overdue_date),
            ])

    @api.model
    def get_or_create_dashboard(self):
        """Get existing dashboard record or create one."""
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({'name': 'Dashboard'})
        return rec.id

    def action_view_draft_settlements(self):
        return {'type': 'ir.actions.act_window', 'name': 'Pending Settlements',
                'res_model': 'settlement.record', 'view_mode': 'list,form',
                'domain': [('state', '=', 'draft')]}

    def action_view_posted_settlements(self):
        return {'type': 'ir.actions.act_window', 'name': 'Awaiting Payment',
                'res_model': 'settlement.record', 'view_mode': 'list,form',
                'domain': [('state', '=', 'posted')]}

    def action_view_low_stock(self):
        return {'type': 'ir.actions.act_window', 'name': 'Low Stock Products',
                'res_model': 'product.template', 'view_mode': 'list,form',
                'domain': [('is_consignment', '=', True),
                           ('qty_available', '<=', 2)]}

    def action_generate_settlements(self):
        return {'type': 'ir.actions.act_window', 'name': 'Generate Settlements',
                'res_model': 'settlement.wizard', 'view_mode': 'form',
                'target': 'new'}
