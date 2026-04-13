/** @odoo-module **/
/**
 * Week 5 — OWL JavaScript Integration
 * Patches Orderline prototype with consignment methods.
 * Two-level commission rate: commission.config override > partner default.
 * Refund lines automatically produce negative payout (no special cases).
 */
import { Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, {
    isConsignment() {
        return this.product?.is_consignment === true;
    },
    getDesignerName() {
        const d = this.product?.designer_id;
        return Array.isArray(d) ? d[1] : null;
    },
    getCommissionRate() {
        const designerId = Array.isArray(this.product?.designer_id)
            ? this.product.designer_id[0] : null;
        if (!designerId) return 0;
        const today = new Date().toISOString().split('T')[0];
        // Level 1: active commission.config
        const active = (this.models?.['commission.config'] || []).find(c => {
            const cid = Array.isArray(c.designer_id) ? c.designer_id[0] : c.designer_id;
            return cid === designerId
                && (!c.date_from || c.date_from <= today)
                && (!c.date_to   || c.date_to   >= today);
        });
        if (active) return active.commission_percentage || 0;
        // Level 2: partner default
        const p = (this.models?.['res.partner'] || []).find(p => p.id === designerId);
        return p?.commission_rate || 0;
    },
    getDesignerPayout() {
        return (this.get_price_without_tax?.() ?? 0) * (1 - this.getCommissionRate() / 100);
    },
    export_for_printing() {
        const r = super.export_for_printing(...arguments);
        if (this.isConsignment()) {
            r.designer_name   = this.getDesignerName();
            r.commission_rate = this.getCommissionRate();
            r.designer_payout = this.getDesignerPayout();
        }
        return r;
    },
});
