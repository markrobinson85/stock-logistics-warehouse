# -*- coding: utf-8 -*-
# © 2015 OdooMRP team
# © 2015 AvanzOSC
# © 2015 Serv. Tecnol. Avanzados - Pedro M. Baeza
# © 2017 Eficent Business and IT Consulting Services S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def _mergeable_domain(self):
        """Return the quants which may be merged with the current record"""
        self.ensure_one()
        return [('id', '!=', self.id),
                ('product_id', '=', self.product_id.id),
                ('lot_id', '=', self.lot_id.id),
                ('package_id', '=', self.package_id.id),
                ('location_id', '=', self.location_id.id),
                ('reservation_id', '=', False),
                ('propagated_from_id', '=', self.propagated_from_id.id),
                ]

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
    def aggressive_merge_stock_quants(self):
        # Get a copy of the recorset
        pending_quants = self.browse(self.ids)
        for quant2merge in self.filtered(lambda x: not x.reservation_id):
            if quant2merge in pending_quants:
                if quant2merge.qty < 0:
                    continue
                quants = self.search(quant2merge._mergeable_domain())
                cont = 1
                cost = quant2merge.cost
                for quant in quants:
                    if quant.qty < 0:
                        continue
                    # Get the latest move.
                    quant2merge_move = quant2merge._get_latest_move()
                    quant_move = quant._get_latest_move()

                    quant_history = quant.history_ids.ids
                    quant_history.remove(quant_move.id)
                    quant2merge_history = quant2merge.history_ids.ids
                    quant2merge_history.remove(quant2merge_move.id)

                    quant_produced_quant_ids = quant.produced_quant_ids.exists().ids
                    qaunt2merge_produced_quant_ids = quant2merge.produced_quant_ids.exists().ids
                    quant_consumed_quant_ids = quant.consumed_quant_ids.exists().ids
                    qaunt2merge_consumed_quant_ids = quant2merge.consumed_quant_ids.exists().ids

                    num_quant_produced_quant_ids = len(quant_produced_quant_ids)
                    num_qaunt2merge_produced_quant_ids = len(qaunt2merge_produced_quant_ids)
                    num_quant_consumed_quant_ids = len(quant_consumed_quant_ids)
                    num_qaunt2merge_consumed_quant_ids = len(qaunt2merge_consumed_quant_ids)

                    # Match one of multiple conditions:
                    #  # -- > Same last move.
                    #  # -- > Same purchase order line.
                    #  # -- > Same production order.
                    #  # -- > Same workcenter operation.
                    #  # -- > Same last picking.
                    #  # -- > Same produced quants and production id on last move
                    #  # -- > Same consumed quants and production id on last move
                    # Assuming the quants only has 1 history each, we can safely assume this is where they originated.
                    if (quant2merge_move.purchase_line_id
                            and quant_move.purchase_line_id
                            and quant2merge_move.purchase_line_id == quant_move.purchase_line_id) \
                        or (quant2merge_move.picking_id
                            and quant_move.picking_id
                            and quant2merge_move.picking_id == quant_move.picking_id) \
                        or (quant2merge_move.raw_material_production_id and
                            quant2merge_move.raw_material_production_id == quant_move.raw_material_production_id and
                            qaunt2merge_produced_quant_ids and
                            num_qaunt2merge_produced_quant_ids and
                            num_quant_produced_quant_ids == num_qaunt2merge_produced_quant_ids and
                            quant_produced_quant_ids == qaunt2merge_produced_quant_ids) \
                        or (quant2merge_move.production_id and
                            quant2merge_move.production_id == quant_move.production_id and
                            qaunt2merge_consumed_quant_ids and
                            num_qaunt2merge_consumed_quant_ids and
                            num_quant_consumed_quant_ids == num_qaunt2merge_consumed_quant_ids and
                            quant_consumed_quant_ids == qaunt2merge_consumed_quant_ids):

                        quant2merge.sudo().qty += quant.qty
                        cost += quant.cost
                        cont += 1
                        pending_quants -= quant

                        # Merge the stock move history removing duplicates.
                        quant2merge.history_ids = [(4, x.id) for x in quant.history_ids if x.picking_id.id not in quant2merge.history_ids.mapped('picking_id').ids or not x.picking_id]

                        quant.with_context(force_unlink=True).sudo().unlink()
                if cost > 0 and cont > 1:
                    quant2merge.sudo().cost = cost / cont

