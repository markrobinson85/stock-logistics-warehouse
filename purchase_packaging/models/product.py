# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

import odoo.addons.decimal_precision as dp


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def _select_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False):
        self.ensure_one()
        res = super(ProductProduct, self)._select_seller(partner_id, quantity, date, uom_id)

        # If no res, iterate again with but ignore min_qty.
        if res.id is False:
            for seller in self.seller_ids:
                # Set quantity in UoM of seller
                quantity_uom_seller = quantity
                if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                    quantity_uom_seller = uom_id._compute_quantity(quantity_uom_seller, seller.product_uom)

                if seller.date_start and seller.date_start > date:
                    continue
                if seller.date_end and seller.date_end < date:
                    continue
                if partner_id and seller.name not in [partner_id, partner_id.parent_id]:
                    continue
                # if quantity_uom_seller < seller.min_qty:
                #     continue
                if seller.product_id and seller.product_id != self:
                    continue

                res |= seller
                break
        return res

