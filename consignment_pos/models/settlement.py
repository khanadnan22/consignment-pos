from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class SettlementRecord(models.Model):

    _name        = 'settlement.record'
    _description = 'Consignment Settlement Record'
    _order       = 'period_start desc'
    _rec_name    = 'designer_id'
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    designer_id       = fields.Many2one('res.partner', string='Designer',
        required=True, domain=[('is_consignor', '=', True)],
        ondelete='restrict', tracking=True)
    total_sales       = fields.Float('Total Sales',        digits=(16, 2), tracking=True)
    commission_amount = fields.Float('Commission (Store)', digits=(16, 2))
    payout_amount     = fields.Float('Payout to Designer', digits=(16, 2), tracking=True)
    period_start      = fields.Date('Period Start', required=True)
    period_end        = fields.Date('Period End',   required=True)

    # Channel breakdown — Week 9
    pos_sales     = fields.Float('POS Sales',     digits=(16, 2),
        help='Sales from in-store POS channel.')
    online_sales  = fields.Float('Online Sales',  digits=(16, 2),
        help='Sales from website/eCommerce channel.')
    pos_payout    = fields.Float('POS Payout',    digits=(16, 2))
    online_payout = fields.Float('Online Payout', digits=(16, 2))

    state = fields.Selection([
        ('draft', 'Draft'), ('posted', 'Posted'), ('disputed', 'Disputed'), ('paid', 'Paid')
    ], default='draft', required=True, tracking=True)

    move_id          = fields.Many2one('account.move', string='Vendor Bill', readonly=True)
    note             = fields.Text('Notes')
    portal_published = fields.Boolean('Visible on Designer Portal', default=False)

    gallery_fee_deduction = fields.Float('Gallery Fee Deduction', digits=(16, 2))
    dispute_reason       = fields.Text('Dispute Reason')
    dispute_date         = fields.Datetime('Dispute Date')
    dispute_response     = fields.Text('Dispute Response')
    dispute_resolved_by  = fields.Many2one('res.users', 'Resolved By')

    has_negative_payout = fields.Boolean(
        compute='_compute_has_negative_payout', store=True, string='Neg. Payout Warning')
    total_order_lines = fields.Integer(
        string='Consignment Lines',
        compute='_compute_total_order_lines', store=True)

    @api.depends('payout_amount')
    def _compute_has_negative_payout(self):
        for rec in self:
            rec.has_negative_payout = rec.payout_amount < 0.0

    @api.depends('period_start', 'period_end', 'designer_id')
    def _compute_total_order_lines(self):
        for rec in self:
            if not rec.period_start or not rec.period_end or not rec.designer_id:
                rec.total_order_lines = 0
                continue
            pos_count = self.env['pos.order.line'].search_count([
                ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
                ('order_id.date_order', '>=', fields.Datetime.to_datetime(str(rec.period_start))),
                ('order_id.date_order', '<=', fields.Datetime.to_datetime(str(rec.period_end) + ' 23:59:59')),
                ('product_id.product_tmpl_id.designer_id', '=', rec.designer_id.id),
                ('product_id.product_tmpl_id.is_consignment', '=', True),
            ])
            sale_count = self.env['sale.order.line'].search_count([
                ('order_id.state', 'in', ['sale', 'done']),
                ('order_id.date_order', '>=', fields.Datetime.to_datetime(str(rec.period_start))),
                ('order_id.date_order', '<=', fields.Datetime.to_datetime(str(rec.period_end) + ' 23:59:59')),
                ('designer_id', '=', rec.designer_id.id),
                ('is_consignment_line', '=', True),
            ])
            rec.total_order_lines = pos_count + sale_count

    @api.constrains('period_start', 'period_end')
    def _check_period(self):
        for rec in self:
            if rec.period_end < rec.period_start:
                raise ValidationError('Period End must be on or after Period Start.')

    # ── State transitions ─────────────────────────────────────────────────────

    def action_post(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only Draft settlements can be posted.')
            if rec.has_negative_payout:
                raise UserError(
                    f'Negative payout for {rec.designer_id.name}. Resolve before posting.')
            if rec.payout_amount > 0 and not rec.move_id:
                rec.move_id = self.env['account.move'].create({
                    'move_type':    'in_invoice',
                    'partner_id':   rec.designer_id.id,
                    'invoice_date': fields.Date.today(),
                    'ref': f'Settlement {rec.period_start} to {rec.period_end}',
                    'invoice_line_ids': [(0, 0, {
                        'name':      f'Consignment Payout {rec.period_start} to {rec.period_end}',
                        'quantity':   1,
                        'price_unit': rec.payout_amount,
                    })],
                })
            rec.state = 'posted'
            rec.portal_published = True
            rec.send_settlement_email()

    def action_mark_paid(self):
        for rec in self:
            if rec.state != 'posted':
                raise UserError('Only Posted can be marked Paid.')
            rec.state = 'paid'

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError('Paid settlements cannot be reset.')
            rec.state = 'draft'
            rec.portal_published = False

    def action_dispute(self):
        self.ensure_one()
        return {
            'name': 'Raise Dispute',
            'type': 'ir.actions.act_window',
            'res_model': 'settlement.dispute.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_settlement_id': self.id},
        }

    def action_resolve_dispute(self):
        self.ensure_one()
        return {
            'name': 'Resolve Dispute',
            'type': 'ir.actions.act_window',
            'res_model': 'settlement.dispute.resolve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_settlement_id': self.id},
        }

    def action_view_bill(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move',
                'res_id': self.move_id.id, 'view_mode': 'form'}

    def action_recalculate(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError('Cannot recalculate a Paid settlement.')
            self._aggregate_for_designer(
                rec.designer_id.id, rec.period_start, rec.period_end, record=rec)

    def send_settlement_email(self):
        tmpl = self.env.ref(
            'consignment_pos.email_template_settlement_posted', raise_if_not_found=False)
        if not tmpl:
            return
        for rec in self:
            if rec.designer_id.email:
                tmpl.send_mail(rec.id, force_send=True)

    def action_send_email(self):
        self.ensure_one()
        self.send_settlement_email()
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Email Sent',
                           'message': f'Email sent to {self.designer_id.name}.',
                           'type': 'success'}}

    def action_print_summary(self):
        """Print monthly/annual designer summary PDF."""
        self.ensure_one()
        return self.env.ref(
            'consignment_pos.action_report_designer_summary'
        ).report_action(self)

    # ── Core aggregation helper ───────────────────────────────────────────────

    def _aggregate_for_designer(self, designer_id, period_start, period_end, record=None):
        """
        Week 9: Unified aggregation across POS + Online channels.
        Returns dict with totals. If record passed, writes to it.
        """
        dt_start = fields.Datetime.to_datetime(str(period_start))
        dt_end   = fields.Datetime.to_datetime(str(period_end) + ' 23:59:59')

        # ── Channel 1: POS ───────────────────────────────────────────────────
        pos_lines = self.env['pos.order.line'].search([
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('order_id.date_order', '>=', dt_start),
            ('order_id.date_order', '<=', dt_end),
            ('product_id.product_tmpl_id.designer_id', '=', designer_id),
            ('product_id.product_tmpl_id.is_consignment', '=', True),
        ])
        pos_sales  = sum(l.price_subtotal       for l in pos_lines)
        pos_payout = sum(l.payout_line_amount for l in pos_lines)

        # ── Channel 2: Website / Sale Orders ─────────────────────────────────
        sale_lines = self.env['sale.order.line'].search([
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', dt_start),
            ('order_id.date_order', '<=', dt_end),
            ('designer_id', '=', designer_id),
            ('is_consignment_line', '=', True),
        ])
        online_sales  = sum(l.price_subtotal       for l in sale_lines)
        online_payout = sum(l.payout_line_amount for l in sale_lines)

        total_sales  = pos_sales  + online_sales
        total_payout = pos_payout + online_payout

        vals = {
            'total_sales':       total_sales,
            'commission_amount': total_sales - total_payout,
            'payout_amount':     total_payout,
            'pos_sales':         pos_sales,
            'pos_payout':        pos_payout,
            'online_sales':      online_sales,
            'online_payout':     online_payout,
        }
        if record:
            record.write(vals)
        return vals

    # ── generate_settlement ───────────────────────────────────────────────────

    @api.model
    def generate_settlement(self, period_start=None, period_end=None, designer_id=None):
        """
        Week 9: Aggregates POS + Website sales for each designer.
        """
        if not period_start or not period_end:
            today       = date.today()
            last_monday = today - timedelta(days=today.weekday() + 7)
            period_start = last_monday
            period_end   = last_monday + timedelta(days=6)

        _logger.info('generate_settlement: %s to %s designer=%s',
                     period_start, period_end, designer_id)

        # Collect all relevant designer IDs from both channels
        dt_start = fields.Datetime.to_datetime(str(period_start))
        dt_end   = fields.Datetime.to_datetime(str(period_end) + ' 23:59:59')

        designer_ids = set()

        pos_lines = self.env['pos.order.line'].search([
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('order_id.date_order', '>=', dt_start),
            ('order_id.date_order', '<=', dt_end),
            ('product_id.product_tmpl_id.is_consignment', '=', True),
        ])
        for l in pos_lines:
            did = l.product_id.product_tmpl_id.designer_id.id
            if did:
                designer_ids.add(did)

        sale_lines = self.env['sale.order.line'].search([
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', dt_start),
            ('order_id.date_order', '<=', dt_end),
            ('is_consignment_line', '=', True),
        ])
        for l in sale_lines:
            if l.designer_id.id:
                designer_ids.add(l.designer_id.id)

        if designer_id:
            designer_ids = {designer_id} if designer_id in designer_ids else set()

        if not designer_ids:
            return self.env['settlement.record']

        created = self.env['settlement.record']
        for did in designer_ids:
            vals = self._aggregate_for_designer(did, period_start, period_end)
            vals.update({'designer_id': did,
                         'period_start': period_start,
                         'period_end':   period_end})
            existing = self.search([
                ('designer_id',  '=', did),
                ('period_start', '=', period_start),
                ('state',        '!=', 'paid'),
            ], limit=1)
            if existing:
                existing.write(vals)
                created |= existing
            else:
                vals['state'] = 'draft'
                created |= self.create(vals)

        _logger.info('generate_settlement done: %d records', len(created))
        return created
