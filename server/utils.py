# -*- coding: utf-8 -*-

import bleach


def filter_input(value):
    return bleach.clean(value)
