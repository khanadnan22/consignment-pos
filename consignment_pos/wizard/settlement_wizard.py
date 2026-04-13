from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta


class SettlementWizard(models.TransientModel):
    """
    Week 6: Manual Settlement Wizard.
    Allows admins to generate settlements for any custom date range
    with optional filter by designer. Live preview shows expected
    order count, designer count, total sales and payout BEFORE generating.
    """
    _name        = 'settlement.wizard'
    _description = 'Generate Settlement Wizard'

    period_start = fields.Date(
        string='Period Start', required=True,
        default=lambda self: date.today() - timedelta(days=date.today().weekday() + 7),
    )
    period_end = fields.Date(
        string='Period End', required=True,
        default=lambda self: date.today() - timedelta(days=date.today().weekday() + 1),
    )
    designer_id = fields.Many2one(
        'res.partner', string='Designer (Optional)',
        domain=[('is_consignor', '=', True)],
        help='Leave empty to generate for ALL designers.',
    )
    # Live preview
    order_count          = fields.Integer(string='Matching Orders',  compute='_compute_preview')
    designer_count       = fields.Integer(string='Designers Found',  compute='_compute_preview')
    total_sales_preview  = fields.Float(string='Total Sales',        compute='_compute_preview', digits=(16,2))
    total_payout_preview = fields.Float(string='Total Payout',       compute='_compute_preview', digits=(16,2))

    @api.depends('period_start', 'period_end', 'designer_id')
    def _compute_preview(self):
        for wiz in self:
            if not wiz.period_start or not wiz.period_end:
                wiz.order_count = wiz.designer_count = 0
                wiz.total_sales_preview = wiz.total_payout_preview = 0.0
                continue
            orders = self.env['pos.order'].search([
                ('state', 'in', ['paid', 'done', 'invoiced']),
                ('date_order', '>=', fields.Datetime.to_datetime(str(wiz.period_start))),
                ('date_order', '<=', fields.Datetime.to_datetime(str(wiz.period_end) + ' 23:59:59')),
            ])
            designers, sales, payout = set(), 0.0, 0.0
            for order in orders:
                for line in order.lines:
                    t = line.product_id.product_tmpl_id
                    if not t.is_consignment or not t.designer_id: continue
                    if wiz.designer_id and t.designer_id.id != wiz.designer_id.id: continue
                    designers.add(t.designer_id.id)
                    sales  += line.price_subtotal
                    payout += line.payout_line_amount
            wiz.order_count          = len(orders)
            wiz.designer_count       = len(designers)
            wiz.total_sales_preview  = sales
            wiz.total_payout_preview = payout

    @api.constrains('period_start', 'period_end')
    def _check_dates(self):
        for wiz in self:
            if wiz.period_start and wiz.period_end and wiz.period_end < wiz.period_start:
                raise UserError('Period End must be on or after Period Start.')

    def action_generate(self):
        self.ensure_one()
        self.env['settlement.record'].generate_settlement(
            period_start=self.period_start,
            period_end=self.period_end,
            designer_id=self.designer_id.id if self.designer_id else None,
        )
        return {
            'type': 'ir.actions.act_window', 'name': 'Pending Settlements',
            'res_model': 'settlement.record', 'view_mode': 'list,form',
            'domain': [('state', '=', 'draft')],
            'target': 'main',
        }
