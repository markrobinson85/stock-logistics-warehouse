# -*- coding: utf-8 -*-
# Copyright 2015-2017 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id',
        comodel_name='product.template',
        readonly=True
    )
    packaging_id = fields.Many2one(
        'product.packaging',
        'Packaging'
    )
    product_purchase_qty = fields.Float(
        'Purchase Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
        required=True, default=lambda *a: 1.0
    )
    product_purchase_uom_id = fields.Many2one(
        'product.uom',
        'Purchase Unit of Measure',
        required=True,
    )

    purchase_price_unit = fields.Float(
        string='Purchase Unit Price',
        store=True,
        readonly=True,
        compute="_compute_product_price",
        digits=dp.get_precision('Product Price'))

    product_qty = fields.Float(
        compute="_compute_product_qty",
        string='Quantity',
        inverse='_inverse_product_qty',
        store=True
    )

    @api.multi
    def _get_product_seller(self):
        self.ensure_one()
        return self.product_id._select_seller(
            partner_id=self.order_id.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and fields.Date.to_string(
                fields.Date.from_string(self.order_id.date_order)) or None,
            uom_id=self.product_uom)

    @api.multi
    @api.depends('price_unit', 'product_purchase_uom_id', 'product_uom')
    def _compute_product_price(self):
        for line in self:
            if line.product_uom.id != line.product_purchase_uom_id.id:
                if line.product_uom.category_id.id == line.product_purchase_uom_id.category_id.id:
                    qty = line.product_purchase_uom_id._compute_quantity(
                        1,
                        line.product_uom
                    )
                    line.purchase_price_unit = qty * line.price_unit
                else:
                    line.purchase_price_unit = line.price_unit
            else:
                line.purchase_price_unit = line.price_unit

    @api.multi
    @api.depends('product_purchase_uom_id',
                 'product_purchase_qty',
                 'product_purchase_uom_id.category_id')
    def _compute_product_qty(self):
        """
        Compute the total quantity
        """
        uom_categories = self.mapped("product_purchase_uom_id.category_id")
        uom_obj = self.env['product.uom']
        to_uoms = uom_obj.search(
            [('category_id',
              'in',
              uom_categories.ids),
             ('uom_type', '=', 'reference')])
        uom_by_category = {to_uom.category_id: to_uom for to_uom in to_uoms}
        for line in self:
            # Convert the qty to the UOM specified on the line.
            if line.product_purchase_uom_id.category_id.id != line.product_uom.category_id.id:
                line.product_qty = line.product_purchase_uom_id._compute_quantity(
                    line.product_purchase_qty,
                    uom_by_category.get(line.product_purchase_uom_id.category_id)
                )
            else:
                line.product_qty = line.product_purchase_uom_id._compute_quantity(
                    line.product_purchase_qty,
                    line.product_uom
                )

    @api.multi
    @api.depends('product_qty')
    def _inverse_product_qty(self):
        """ If product_quantity is set compute the purchase_qty
        """
        uom_categories = self.mapped("product_purchase_uom_id.category_id")
        uom_obj = self.env['product.uom']
        from_uoms = uom_obj.search(
            [('category_id',
              'in',
              uom_categories.ids),
             ('uom_type', '=', 'reference')])
        uom_by_category = {from_uom.category_id: from_uom for from_uom in from_uoms}
        for line in self:
            if line.product_id:
                supplier = line._get_product_seller()
                if supplier.id and supplier.min_qty_uom_id.id:
                    product_purchase_uom = supplier.min_qty_uom_id
                    from_uom = uom_by_category.get(product_purchase_uom.category_id)
                    if line.product_uom.category_id.id != product_purchase_uom.category_id.id:
                        line.product_purchase_qty = from_uom._compute_quantity(
                            line.product_qty,
                            product_purchase_uom)
                    else:
                        line.product_purchase_qty = line.product_uom._compute_quantity(
                            line.product_qty,
                            product_purchase_uom)
                    line.product_purchase_uom_id = product_purchase_uom.id
                else:
                    line.product_purchase_uom_id = line.product_uom.id
                    line.product_purchase_qty = line.product_qty
            else:
                line.product_purchase_qty = line.product_qty

    @api.onchange("packaging_id")
    def _onchange_packaging_id(self):
        if self.packaging_id:
            self.product_uom = self.packaging_id.uom_id

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ set domain on product_purchase_uom_id and packaging_id
            set the first packagigng, purchase_uom and purchase_qty
        """
        domain = {}
        # call default implementation
        # restore default values
        defaults = self.default_get(
            ['packaging_id', 'product_purchase_uom_id'])
        self.packaging_id = self.packaging_id.browse(
            defaults.get('packaging_id', []))
        self.product_purchase_uom_id = self.product_purchase_uom_id.browse(
            defaults.get('product_purchase_uom_id', []))
        # add default domains
        if self.product_id and self.partner_id:
            domain['packaging_id'] = [
                ('id', 'in', self.product_id.mapped(
                    'seller_ids.packaging_id.id'))]
            domain['product_purchase_uom_id'] = \
                [('id', 'in', self.product_id.mapped(
                    'seller_ids.min_qty_uom_id.id'))]
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.product_id:
            supplier = self._get_product_seller()
        else:
            supplier = self.product_id.seller_ids.browse([])
        if supplier.product_uom:
            # use the uom from the suppleir
            self.product_uom = supplier.product_uom
        if supplier.min_qty_uom_id:
            # if the supplier requires some min qty/uom,
            self.product_purchase_qty = supplier.min_qty
            self.product_purchase_uom_id = supplier.min_qty_uom_id
            domain['product_purchase_uom_id'] = \
                [('id', '=', supplier.min_qty_uom_id.id)]
            to_uom = self.env['product.uom'].search([
                ('category_id', '=',
                 supplier.min_qty_uom_id.category_id.id),
                ('uom_type', '=', 'reference')], limit=1)
            to_uom = to_uom and to_uom[0]
            if self.product_purchase_uom_id.category_id.id != self.product_uom.category_id.id:
                self.product_qty = supplier.min_qty_uom_id._compute_quantity(
                    supplier.min_qty, to_uom
                )
            else:
                self.product_qty = supplier.min_qty_uom_id._compute_quantity(
                    supplier.min_qty, self.product_uom
                )
        self.packaging_id = supplier.packaging_id
        if self.product_purchase_uom_id.id is False:
            self.product_purchase_uom_id = self.product_uom.id

        if domain:
            if res.get('domain'):
                res['domain'].update(domain)
            else:
                res['domain'] = domain  # pragma: no cover not aware of super
        return res

    @api.multi
    def _prepare_stock_moves(self, picking):
        self.ensure_one()
        val = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        for v in val:
            v['product_packaging'] = self.packaging_id.id
        return val

    @api.model
    def update_vals(self, vals):
        """
        When packaging_id is set, uom_id is readonly,
        so we need to reset the uom value in the vals dict
        TODO: Fix this.
        """
        if vals.get('packaging_id'):
            if vals.get('product_id') and vals.get('product_uom') and isinstance(vals.get('product_uom'), basestring) is False:
                vals['product_uom'] = self.env['product.product'].browse(vals['product_id']).uom_po_id.id

                vals['product_purchase_uom_id'] = self.env['product.packaging'].browse(
                    vals['packaging_id']).uom_id.id

        return vals

    @api.model
    @api.returns('self', lambda rec: rec.id)
    def create(self, vals):
        if 'product_qty' not in vals and 'product_purchase_qty' in vals:
            # compute product_qty to avoid inverse computation and reset to 1
            uom_obj = self.env['product.uom']
            product_uom = uom_obj.browse(vals['product_uom'])
            product_purchase_uom = uom_obj.browse(vals['product_purchase_uom_id'])

            # Convert the qty to the UOM specified on the line.
            if product_purchase_uom.category_id.id != product_uom.category_id.id:
                vals['product_qty'] = product_purchase_uom._compute_quantity(
                    vals['product_purchase_qty'],
                    uom_by_category.get(product_purchase_uom.category_id)
                )
            else:
                vals['product_qty'] = product_purchase_uom._compute_quantity(
                    vals['product_purchase_qty'],
                    product_uom
                )

        elif 'product_qty' in vals and 'product_purchase_qty' not in vals and 'product_purchase_uom_id' not in vals:
            # Handle cases where product's vendor's uom may not be set, or not passed through.
            vals['product_purchase_qty'] = vals['product_qty']
            vals['product_purchase_uom_id'] = vals['product_uom']

        return super(PurchaseOrderLine, self).create(self.update_vals(vals))

    @api.multi
    def write(self, vals):
        return super(PurchaseOrderLine, self).write(self.update_vals(vals))
