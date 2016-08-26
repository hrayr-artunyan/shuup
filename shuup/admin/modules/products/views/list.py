# -*- coding: utf-8 -*-
# This file is part of Shuup.
#
# Copyright (c) 2012-2016, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals
import six

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.http.response import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text

from django.views.generic.edit import FormView

from shuup import configuration
from shuup.admin.toolbar import get_default_edit_toolbar
from shuup.admin.utils.picotable import ChoicesFilter, Column, TextFilter
from shuup.admin.utils.views import PicotableListView
from shuup.core.models import Category, Product, ProductMode


product_list_columns = [
    Column("sku", _(u"SKU"), display="sku", filter_config=TextFilter(placeholder=_("Filter by SKU..."))),
    Column("name", _(u"Name"), sort_field="translations__name", display="name", filter_config=TextFilter(
        filter_field="translations__name",
        placeholder=_("Filter by name...")
    )),
    Column("barcode", _(u"Barcode"), display="barcode", filter_config=TextFilter(_("Filter by barcode..."))),
    Column("type", _(u"Type")),
    Column("mode", _(u"Mode"), filter_config=ChoicesFilter(ProductMode.choices)),
    Column("category", _(u"Primary Category"), filter_config=ChoicesFilter(Category.objects.all(), "category")),
]

PRODUCT_KEY_TEMPLATE = "product_list_%s"


class ProductListView(PicotableListView):
    model = Product

    def __init__(self, *args, **kwargs):
        super(ProductListView, self).__init__(*args, **kwargs)

        self.columns = [column for column in product_list_columns
                        if configuration.get(None, PRODUCT_KEY_TEMPLATE % column.id)]

    def get_queryset(self):
        filter = self.get_filter()
        shop_id = filter.get("shop")
        qs = Product.objects.all_except_deleted()
        q = Q()
        for mode in filter.get("modes", []):
            q |= Q(mode=mode)
        manufacturer_ids = filter.get("manufacturers")
        if manufacturer_ids:
            q |= Q(manufacturer_id__in=manufacturer_ids)
        qs = qs.filter(q)
        if shop_id:
            qs = qs.filter(shop_products__shop_id=int(shop_id))
        return qs

    def get_object_abstract(self, instance, item):
        return [
            {"text": "%s" % instance, "class": "header"},
            {"title": _(u"Barcode"), "text": item.get("barcode", None)},
            {"title": _(u"SKU"), "text": item.get("sku", None)},
            {"title": _(u"Type"), "text": item.get("type", None)},
            {"title": _(u"Primary Category"), "text": item.get("category", None)}
        ]


class SettingsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(SettingsForm, self).__init__(*args, **kwargs)

        for col in product_list_columns:
            self.fields[PRODUCT_KEY_TEMPLATE % col.id] = forms.BooleanField(label=col.title, required=False)


class ProductSettingsView(FormView):
    form_class = SettingsForm
    template_name = "shuup/admin/products/edit_settings.jinja"

    def get_initial(self):
        initial = super(ProductSettingsView, self).get_initial()

        for col in product_list_columns:
            key = PRODUCT_KEY_TEMPLATE % col.id
            initial.update({
                key: bool(configuration.get(None, key))
            })
        return initial

    def form_valid(self, form):
        for col, val in six.iteritems(form.cleaned_data):
            configuration.set(None, col, val)

        messages.success(self.request, _("Product settings saved"))
        return HttpResponseRedirect(self.request.path)

    def get_context_data(self, **kwargs):
        context = super(ProductSettingsView, self).get_context_data(**kwargs)
        context["toolbar"] = get_default_edit_toolbar(self, "product_settings_form", with_split_save=False)

        return context
