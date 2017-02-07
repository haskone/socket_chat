# -*- coding: utf-8 -*-

import bleach


def filter_input(value):
    value = value.replace(':', '')
    return bleach.clean(value)
