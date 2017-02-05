# -*- coding: utf-8 -*-

import random

import requests
from lxml import html


class Bot(object):

    @classmethod
    def process(cls, data, logger):
        if 'news' == data:
            logger.debug('try to get news')
            return cls.news_handler(logger)
        elif data.startswith('sum of '):
            logger.debug("sum of '%s' / %s" % (data[7:], str(data[7:].split(' '))))
            return cls.sum_handler(data[7:])
        elif data.startswith('mean of '):
            logger.debug("mean of '%s'" % data[8:])
            return cls.mean_handler(data[8:])

    @classmethod
    def _get_numbers(cls, data):
        number_arr = data.split(' ')
        try:
            numbers = [float(number.strip()) for number in number_arr if number.strip()]
        except ValueError:
            return 'Something wrong with your input. Please give me only numbers'
        else:
            return numbers

    @classmethod
    def mean_handler(cls, data):
        result = cls._get_numbers(data)
        if isinstance(result, list):
            return 'Result mean of %s is %s' % (str(result), sum(result) / len(result))
        else:
            return result

    @classmethod
    def sum_handler(cls, data):
        result = cls._get_numbers(data)
        if isinstance(result, list):
            return 'Result sum of %s is %s' % (str(result), sum(result))
        else:
            return result

    # TODO: yeah, it's not an appropriate way.
    # TODO: Need to a separate service for such long operations
    @classmethod
    def news_handler(cls, logger):
        r = requests.get('https://news.ycombinator.com/')
        tree = html.fromstring(r.content)
        trs = tree.xpath('//table[@class="itemlist"]/tr')
        texts = trs[0].xpath('//a[@class="storylink"]/text()')

        item_number = random.randint(0, len(texts) - 1)
        text = texts[item_number]
        href = trs[0].xpath('//a[@class="storylink"]')[item_number].attrib['href']

        logger.debug('got "%s" with href "%s"' % (text, href))
        return '%s</br>(see more here %s)' % (text, href)
