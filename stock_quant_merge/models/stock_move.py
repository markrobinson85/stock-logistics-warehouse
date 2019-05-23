# -*- coding: utf-8 -*-
# © 2017 Eficent Business and IT Consulting Services S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def quants_unreserve(self):
        for move in self:
            quants = move.reserved_quant_ids
            super(StockMove, move).quants_unreserve()
            quants.merge_stock_quants()

    @api.multi
    def action_done(self):
        res = super(StockMove, self).action_done()
        for move in self:
            move.quant_ids.aggressive_merge_stock_quants()
        return res

