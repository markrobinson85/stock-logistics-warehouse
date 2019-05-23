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

    # @api.model
    # def quants_move(self, quants, move, location_to, location_from=False, lot_id=False, owner_id=False,
    #                 src_package_id=False, dest_package_id=False, entire_pack=False):
    #     res = super(StockQuant, self).quants_move(quants=quants, move=move, location_to=location_to, location_from=location_from, lot_id=lot_id, owner_id=owner_id,
    #                 src_package_id=src_package_id, dest_package_id=dest_package_id, entire_pack=entire_pack)
    #     quants.merge_stock_quants()
    #     return res

    @api.multi
    def aggressive_merge_stock_quants(self):
        # Get a copy of the recorset
        pending_quants = self.browse(self.ids)
        for quant2merge in self.filtered(lambda x: not x.reservation_id):
            if quant2merge in pending_quants:
                quants = self.search(quant2merge._mergeable_domain())
                cont = 1
                cost = quant2merge.cost
                for quant in quants:
                    # Get the latest move.
                    quant2merge_move = quant2merge._get_latest_move()
                    quant_move = quant._get_latest_move()

                    quant_history = quant.history_ids.ids
                    quant_history.remove(quant_move.id)
                    quant2merge_history = quant2merge.history_ids.ids
                    quant2merge_history.remove(quant2merge_move.id)

                    # TODO: Test this.
                    # If the latest move matches, merge, otherwise we want to make sure the history of the quant is
                    # only 1 move deep; or check that the histories (minus latest move) is an exact match.
                    # Make sure the latest move is
                    # if quant2merge_move.id == quant_move.id:
                    #     continue
                    # if (quant2merge_move.id == quant_move.id) \
                    #     or ((len(quant.history_ids) > 1 and len(quant2merge.history_ids) > 1)\
                    #     and (set(quant_history) != set(quant2merge_history))):
                    #     continue

                    # Match one of multiple conditions:
                    #  # -- > Same last move.
                    #  # -- > Same purchase order line.
                    #  # -- > Same production order.
                    #  # -- > Same workcenter operation.
                    #  # -- > Same last picking.
                    # Assuming the quants only has 1 history each, we can safely assume this is where they originated.
                    if (quant2merge_move.id == quant_move.id)\
                            or (quant2merge_move.purchase_line_id
                                and quant_move.purchase_line_id
                                and quant2merge_move.purchase_line_id == quant_move.purchase_line_id) \
                            or (quant2merge_move.production_id
                                and quant_move.production_id
                                and quant2merge_move.production_id == quant_move.production_id) \
                            or (quant2merge_move.picking_id
                                and quant_move.picking_id
                                and quant2merge_move.picking_id == quant_move.picking_id) \
                            or (quant2merge_move.raw_material_production_id
                                and quant_move.raw_material_production_id
                                and quant2merge_move.raw_material_production_id == quant_move.raw_material_production_id):
                        quant2merge.sudo().qty += quant.qty
                        cost += quant.cost
                        cont += 1
                        pending_quants -= quant

                        # Link moves to the merged stock quants.
                        # TODO: Is it necessary to retain the other move?
                        # Don't retain move line if quant originated at production id.
                        # and not quant2merge_move.production_id
                        # if quant2merge_move.id != quant_move.id and set(quant_history) == set(quant2merge_history):
                        # if quant2merge_move.id != quant_move.id:
                        quant2merge.history_ids = [(4, quant_move.id)]

                        # Merge consumed quants and produced quants
                        if quant.consumed_quant_ids:
                            quant2merge.consumed_quant_ids = [(4, x.id) for x in quant.consumed_quant_ids]
                        if quant.produced_quant_ids:
                            quant2merge.produced_quant_ids = [(4, x.id) for x in quant.produced_quant_ids]

                        # elif quant2merge_move.id != quant_move.id and len(quant2merge.history_ids) > 1:
                        #     quant2merge.history_ids += [(4, x.id) for x in quant.history_ids]
                        quant.with_context(force_unlink=True).sudo().unlink()

                quant2merge.sudo().cost = cost / cont

