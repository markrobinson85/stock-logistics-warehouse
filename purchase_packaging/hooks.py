# -*- coding: utf-8 -*-
# Copyright 2015-2017 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def post_init_hook(cr, registry):
    cr.execute("""UPDATE purchase_order_line
                  SET 
                      product_purchase_qty = product_qty,
                      product_purchase_uom_id = product_uom,
                      purchase_price_unit = price_unit
                  """)
    cr.execute("""UPDATE product_supplierinfo
                      SET purchase_price = price""")
