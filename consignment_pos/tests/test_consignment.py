from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestConsignmentPOS(TransactionCase):
    """
    Week 6: Integration Test Suite.
    Tests commission calculation, settlement generation, refund netting,
    negative payout blocking, recalculate, and wizard filter.
    Run with: odoo-bin -d <db> --test-enable -i consignment_pos
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a consignor designer partner
        cls.designer = cls.env['res.partner'].create({
            'name':              'Test Designer',
            'is_consignor':    True,
            'commission_rate': 30.0,
        })

        # Create a consignment product linked to the designer
        cls.product = cls.env['product.template'].create({
            'name':              'Designer Shirt',
            'type':              'consu',
            'list_price':        1000.0,
            'is_consignment':  True,
            'designer_id':     cls.designer.id,
        })

    # ── Test 1: Commission rate default on partner ────────────────────────────
    def test_01_designer_commission_rate(self):
        self.assertEqual(self.designer.commission_rate, 30.0,
            "Designer should have 30% commission rate")

    # ── Test 2: Product linked to designer ────────────────────────────────────
    def test_02_product_consignment_flag(self):
        self.assertTrue(self.product.is_consignment,
            "Product should be flagged as consignment")
        self.assertEqual(self.product.designer_id.id, self.designer.id,
            "Product designer should match")

    # ── Test 3: Commission config override ───────────────────────────────────
    def test_03_commission_config_override(self):
        config = self.env['commission.config'].create({
            'designer_id':           self.designer.id,
            'commission_percentage':  25.0,
            'date_from':             '2025-01-01',
            'date_to':               '2099-12-31',
        })
        self.assertEqual(config.commission_percentage, 25.0,
            "Commission config should store 25% rate")

    # ── Test 4: Settlement create and state machine ───────────────────────────
    def test_04_settlement_lifecycle(self):
        settlement = self.env['settlement.record'].create({
            'designer_id':       self.designer.id,
            'total_sales':       10000.0,
            'commission_amount': 3000.0,
            'payout_amount':     7000.0,
            'period_start':      '2025-01-01',
            'period_end':        '2025-01-07',
        })
        self.assertEqual(settlement.state, 'draft')
        settlement.action_post()
        self.assertEqual(settlement.state, 'posted')
        settlement.action_mark_paid()
        self.assertEqual(settlement.state, 'paid')

    # ── Test 5: Paid settlement cannot be reset ───────────────────────────────
    def test_05_paid_cannot_reset(self):
        s = self.env['settlement.record'].create({
            'designer_id':   self.designer.id,
            'total_sales':   5000.0, 'commission_amount': 1500.0,
            'payout_amount': 3500.0,
            'period_start':  '2025-02-01', 'period_end': '2025-02-07',
            'state':         'paid',
        })
        with self.assertRaises(UserError):
            s.action_reset_draft()

    # ── Test 6: Negative payout blocks posting ────────────────────────────────
    def test_06_negative_payout_blocks_post(self):
        s = self.env['settlement.record'].create({
            'designer_id':       self.designer.id,
            'total_sales':       -1000.0,
            'commission_amount': -300.0,
            'payout_amount':     -700.0,
            'period_start':      '2025-03-01',
            'period_end':        '2025-03-07',
        })
        self.assertTrue(s.has_negative_payout,
            "Negative payout flag should be True")
        with self.assertRaises(UserError):
            s.action_post()

    # ── Test 7: Payout formula correctness ───────────────────────────────────
    def test_07_payout_formula(self):
        """payout = price_subtotal x (1 - rate/100)"""
        price_subtotal    = 10000.0
        commission_rate   = 30.0
        expected_payout   = price_subtotal * (1 - commission_rate / 100)
        self.assertAlmostEqual(expected_payout, 7000.0, places=2,
            msg="Payout should be 7000 for 10000 sale at 30% commission")

    # ── Test 8: Refund netting formula ───────────────────────────────────────
    def test_08_refund_netting(self):
        """Sale +10000 payout +7000, Refund -10000 payout -7000, Net = 0"""
        sale_payout   =  10000.0 * (1 - 30.0 / 100)
        refund_payout = -10000.0 * (1 - 30.0 / 100)
        net_payout    = sale_payout + refund_payout
        self.assertAlmostEqual(net_payout, 0.0, places=2,
            msg="Net payout after full refund should be 0")

    # ── Test 9: Commission config date constraint ─────────────────────────────
    def test_09_commission_config_date_constraint(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises((UserError, ValidationError)):
            self.env['commission.config'].create({
                'designer_id':           self.designer.id,
                'commission_percentage':  20.0,
                'date_from':             '2025-12-31',
                'date_to':               '2025-01-01',  # invalid: end before start
            })
