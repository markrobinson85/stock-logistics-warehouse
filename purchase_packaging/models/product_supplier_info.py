# -*- coding: utf-8 -*-
# Copyright 2015-2017 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    packaging_id = fields.Many2one(
        'product.packaging',
        'Logisitical Units',
        help='Tip: If the bag you just created is not showing here, save the product and try again.'
    )
    product_uom = fields.Many2one(
        compute='_compute_product_uom',
        string="Supplier Unit of Measure",
        related=False
    )

    min_qty_uom_id = fields.Many2one(
        'product.uom',
        'Minimal Unit of Measure Quantity',
    )

    purchase_price = fields.Float(string='Package Price', required=False, store=False,
                                  compute="_get_purchase_price", digits=dp.get_precision('Product Price'),
                                  readonly=True)

    @api.one
    @api.depends('price', 'min_qty_uom_id')
    def _get_purchase_price(self):
        if self.product_uom.id != self.min_qty_uom_id.id and self.min_qty_uom_id.id is not False:
            if self.product_uom.category_id.id == self.min_qty_uom_id.category_id.id:
                qty = self.min_qty_uom_id._compute_quantity(
                    1,
                    self.product_uom
                )
                self.purchase_price = qty * self.price
        else:
            self.purchase_price = self.price

    def _set_purchase_price(self):
        return

    @api.multi
    @api.depends('product_tmpl_id', 'packaging_id')
    def _compute_product_uom(self):
        """ Set product_uom as a computed field instead of a related field.
            To use uom of link packaging
        """
        for rec in self:
            rec.product_uom = rec.packaging_id.uom_id or \
                rec.product_id.uom_po_id or \
                rec.product_tmpl_id.uom_po_id

