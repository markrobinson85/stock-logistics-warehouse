# -*- coding: utf-8 -*-
# © 2015 OdooMRP team
# © 2015 AvanzOSC
# © 2015 Serv. Tecnol. Avanzados - Pedro M. Baeza
# © 2017 Eficent Business and IT Consulting Services S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from odoo.addons.queue_job.job import job


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def _get_latest_move(self):
        latest_move = self.history_ids.sorted(lambda x: x.date)[0]
        return latest_move

    @api.multi
    def _mergeable_domain(self):
        """Return the quants which may be merged with the current record"""
        self.ensure_one()
        return [('id', '!=', self.id),
                ('product_id', '=', self.product_id.id),
                ('lot_id', '=', self.lot_id.id),
                ('package_id', '=', self.package_id.id),
                ('location_id', '=', self.location_id.id),
                # ('location_id.usage', '=', 'internal'),
                # ('location_id.usage', '=', 'internal'),
                ('location_id.scrap_location', '=', False),
                ('reservation_id', '=', False),
                ('propagated_from_id', '=', self.propagated_from_id.id),
                # '|', '|',
                # ('location_id.usage', '=', 'internal'),
                # ('history_ids', 'in', self.ids)
                ]
        # return [('id', '!=', self.id),
        #         ('product_id', '=', self.product_id.id),
        #         ('lot_id', '=', self.lot_id.id),
        #         ('package_id', '=', self.package_id.id),
        #         ('location_id', '=', self.location_id.id),
        #         # ('location_id.usage', '=', 'internal'),
        #         ('location_id.scrap_location', '=', False),
        #         ('reservation_id', '=', False),
        #         ('propagated_from_id', '=', self.propagated_from_id.id),
        #         ]

    @api.multi
    def merge_stock_quants(self):
        # Get a copy of the recorset
        pending_quants = self.browse(self.ids)
        for quant2merge in self.filtered(lambda x: not x.reservation_id):
            if quant2merge in pending_quants:
                quants = self.search(quant2merge._mergeable_domain())
                cont = 1
                cost = quant2merge.cost
                for quant in quants:
                    if (quant2merge._get_latest_move() ==
                            quant._get_latest_move()):
                        quant2merge.sudo().qty += quant.qty
                        cost += quant.cost
                        cont += 1
                        pending_quants -= quant
                        quant.with_context(force_unlink=True).sudo().unlink()
                quant2merge.sudo().cost = cost / cont

    @api.multi
    @job
    def queue_aggressive_merge_stock_quants(self):
        # Get a copy of the recorset
        pending_quants = self.browse(self.ids)
        for quant2merge in self.filtered(lambda x: not x.reservation_id):
            if not quant2merge.exists():
                continue
            # if quant2merge.location_id.scrap_location:
            #     # Don't merge at scrap locations.
            #     continue
            if quant2merge in pending_quants:
                if quant2merge.qty < 0:
                    continue

                quants = self.search(quant2merge._mergeable_domain())
                cont = 1
                cost = quant2merge.cost
                quant2merge_move = quant2merge._get_latest_move()

                for quant in quants:
                    if quant.qty < 0:
                        continue
                    # Get the latest move.
                    quant_move = quant._get_latest_move()

                    if quant.location_id.usage != 'internal':
                        if quant_move != quant2merge_move:
                            continue
                        if set(quant.mapped('history_ids.raw_material_production_id').ids) != set(
                                quant2merge.mapped('history_ids.raw_material_production_id').ids):
                            continue
                        if set(quant.mapped('history_ids.production_id').ids) != set(
                                quant2merge.mapped('history_ids.production_id').ids):
                            continue

                    quant2merge.sudo().qty += quant.qty
                    cost += quant.cost
                    cont += 1
                    pending_quants -= quant

                    # Merge the stock move history removing duplicates.
                    quant2merge.sudo().history_ids = [(4, x.id) for x in quant.history_ids if
                                                      x.picking_id.id not in quant2merge.history_ids.mapped(
                                                          'picking_id').ids or not x.picking_id]

                    # Merge consumed quants and produced quants
                    if quant.sudo().consumed_quant_ids:
                        quant2merge.sudo().consumed_quant_ids = [(4, x.id) for x in quant.consumed_quant_ids if
                                                                 x.exists()]
                    if quant.sudo().produced_quant_ids:
                        quant2merge.sudo().produced_quant_ids = [(4, x.id) for x in quant.produced_quant_ids if
                                                                 x.exists()]

                    if quant.exists():
                        quant.with_context(force_unlink=True).sudo().unlink()
                if cost > 0 and cont > 1:
                    quant2merge.sudo().cost = cost / cont

    @api.multi
    def aggressive_merge_stock_quants(self):
        self.with_delay().queue_aggressive_merge_stock_quants()

