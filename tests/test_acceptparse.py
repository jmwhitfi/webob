import re

import pytest

from webob.acceptparse import (
    _item_n_weight_re,
    _list_1_or_more__compiled_re,
    Accept,
    AcceptCharset,
    AcceptLanguage,
    AcceptLanguageInvalidHeader,
    AcceptLanguageNoHeader,
    AcceptLanguageValidHeader,
    accept_language_property,
    accept_property,
    create_accept_language_header,
    MIMEAccept,
    NilAccept,
    NoAccept,
)
from webob.request import Request


class Test_ItemNWeightRe(object):
    @pytest.mark.parametrize('header_value', [
        'q=',
        'q=1',
        ';q',
        ';q=',
        ';q=1',
        'foo;',
        'foo;q',
        'foo;q1',
        'foo;q=',
        'foo;q=-1',
        'foo;q=2',
        'foo;q=1.001',
        'foo;q=0.0001',
        'foo;q=00',
        'foo;q=01',
        'foo;q=00.1',
        'foo,q=0.1',
        'foo;q =1',
        'foo;q= 1',
    ])
    def test_invalid(self, header_value):
        regex = _item_n_weight_re(item_re='foo')
        assert re.match('^' + regex + '$', header_value, re.VERBOSE) is None

    @pytest.mark.parametrize('header_value, groups', [
        ('foo', ('foo', None)),
        ('foo;q=0', ('foo', '0')),
        ('foo;q=0.0', ('foo', '0.0')),
        ('foo;q=0.00', ('foo', '0.00')),
        ('foo;q=0.000', ('foo', '0.000')),
        ('foo;q=1', ('foo', '1')),
        ('foo;q=1.0', ('foo', '1.0')),
        ('foo;q=1.00', ('foo', '1.00')),
        ('foo;q=1.000', ('foo', '1.000')),
        ('foo;q=0.1', ('foo', '0.1')),
        ('foo;q=0.87', ('foo', '0.87')),
        ('foo;q=0.382', ('foo', '0.382')),
        ('foo;Q=0.382', ('foo', '0.382')),
        ('foo ;Q=0.382', ('foo', '0.382')),
        ('foo; Q=0.382', ('foo', '0.382')),
        ('foo  ;  Q=0.382', ('foo', '0.382')),
    ])
    def test_valid(self, header_value, groups):
        regex = _item_n_weight_re(item_re='foo')
        assert re.match(
            '^' + regex + '$', header_value, re.VERBOSE,
        ).groups() == groups


class Test_List1OrMoreCompiledRe(object):
    @pytest.mark.parametrize('header_value', [
        # RFC 7230 Section 7
        ',',
        ',   ,',
        # RFC 7230 Errata ID: 4169
        'foo , ,bar,charlie   ',
        # Our tests
        ' foo , ,bar,charlie',
        ' ,foo , ,bar,charlie',
        ',foo , ,bar,charlie, ',
        '\tfoo , ,bar,charlie',
        '\t,foo , ,bar,charlie',
        ',foo , ,bar,charlie\t',
        ',foo , ,bar,charlie,\t',
    ])
    def test_invalid(self, header_value):
        regex = _list_1_or_more__compiled_re(element_re='([a-z]+)')
        assert regex.match(header_value) is None

    @pytest.mark.parametrize('header_value', [
        # RFC 7230 Section 7
        'foo,bar',
        'foo, bar,',
        # RFC 7230 Errata ID: 4169
        'foo , ,bar,charlie',
        # Our tests
        'foo , ,bar,charlie',
        ',foo , ,bar,charlie',
        ',foo , ,bar,charlie,',
        ',\t ,,,  \t \t,   ,\t\t\t,foo \t\t,, bar,  ,\tcharlie \t,,  ,',
    ])
    def test_valid(self, header_value):
        regex = _list_1_or_more__compiled_re(element_re='([a-z]+)')
        assert regex.match(header_value)


def test_parse_accept_badq():
    assert list(Accept.parse("value1; q=0.1.2")) == [('value1', 1)]

def test_init_accept_content_type():
    accept = Accept('text/html')
    assert accept.parsed == [('text/html', 1)]

def test_init_accept_accept_charset():
    accept = AcceptCharset('iso-8859-5, unicode-1-1;q=0.8')
    assert accept.parsed == [('iso-8859-5', 1),
                             ('unicode-1-1', 0.80000000000000004),
                             ('iso-8859-1', 1)]

def test_init_accept_accept_charset_mixedcase():
    """3.4 Character Sets
           [...]
           HTTP character sets are identified by case-insensitive tokens."""
    accept = AcceptCharset('ISO-8859-5, UNICODE-1-1;q=0.8')
    assert accept.parsed == [('iso-8859-5', 1),
                             ('unicode-1-1', 0.80000000000000004),
                             ('iso-8859-1', 1)]

def test_init_accept_accept_charset_with_iso_8859_1():
    accept = Accept('iso-8859-1')
    assert accept.parsed == [('iso-8859-1', 1)]

def test_init_accept_accept_charset_wildcard():
    accept = Accept('*')
    assert accept.parsed == [('*', 1)]

def test_accept_repr():
    accept = Accept('text/html')
    assert repr(accept) == "<Accept('text/html')>"

def test_accept_str():
    accept = Accept('text/html')
    assert str(accept) == 'text/html'

def test_zero_quality():
    assert Accept('bar, *;q=0').best_match(['foo']) is None
    assert 'foo' not in Accept('*;q=0')


def test_accept_str_with_q_not_1():
    value = 'text/html;q=0.5'
    accept = Accept(value)
    assert str(accept) == value

def test_accept_str_with_q_not_1_multiple():
    value = 'text/html;q=0.5, foo/bar'
    accept = Accept(value)
    assert str(accept) == value

def test_accept_add_other_accept():
    accept = Accept('text/html') + Accept('foo/bar')
    assert str(accept) == 'text/html, foo/bar'
    accept += Accept('bar/baz;q=0.5')
    assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'

def test_accept_add_other_list_of_tuples():
    accept = Accept('text/html')
    accept += [('foo/bar', 1)]
    assert str(accept) == 'text/html, foo/bar'
    accept += [('bar/baz', 0.5)]
    assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'
    accept += ['she/bangs', 'the/house']
    assert str(accept) == ('text/html, foo/bar, bar/baz;q=0.5, '
                           'she/bangs, the/house')

def test_accept_add_other_dict():
    accept = Accept('text/html')
    accept += {'foo/bar': 1}
    assert str(accept) == 'text/html, foo/bar'
    accept += {'bar/baz': 0.5}
    assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'

def test_accept_add_other_empty_str():
    accept = Accept('text/html')
    accept += ''
    assert str(accept) == 'text/html'

def test_accept_with_no_value_add_other_str():
    accept = Accept('')
    accept += 'text/html'
    assert str(accept) == 'text/html'

def test_contains():
    accept = Accept('text/html')
    assert 'text/html' in accept

def test_contains_not():
    accept = Accept('text/html')
    assert not 'foo/bar' in accept

def test_quality():
    accept = Accept('text/html')
    assert accept.quality('text/html') == 1
    accept = Accept('text/html;q=0.5')
    assert accept.quality('text/html') == 0.5

def test_quality_not_found():
    accept = Accept('text/html')
    assert accept.quality('foo/bar') is None

def test_best_match():
    accept = Accept('text/html, foo/bar')
    assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
    assert accept.best_match(['foo/bar', 'text/html']) == 'foo/bar'
    assert accept.best_match([('foo/bar', 0.5),
                              'text/html']) == 'text/html'
    assert accept.best_match([('foo/bar', 0.5),
                              ('text/html', 0.4)]) == 'foo/bar'
    with pytest.raises(ValueError):
        accept.best_match(['text/*'])

def test_best_match_with_one_lower_q():
    accept = Accept('text/html, foo/bar;q=0.5')
    assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
    accept = Accept('text/html;q=0.5, foo/bar')
    assert accept.best_match(['text/html', 'foo/bar']) == 'foo/bar'


def test_best_match_with_complex_q():
    accept = Accept('text/html, foo/bar;q=0.55, baz/gort;q=0.59')
    assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
    accept = Accept('text/html;q=0.5, foo/bar;q=0.586, baz/gort;q=0.5966')
    assert "baz/gort;q=0.597" in str(accept)
    assert "foo/bar;q=0.586" in str(accept)
    assert "text/html;q=0.5" in str(accept)
    assert accept.best_match(['text/html', 'baz/gort']) == 'baz/gort'


def test_accept_match():
    for mask in ['*', 'text/html', 'TEXT/HTML']:
        assert 'text/html' in Accept(mask)
    assert 'text/html' not in Accept('foo/bar')


def test_accept_iter():
    accept = Accept(
        'text/plain; q=0.5, text/html; q=0, text/x-dvi; q=0.8, text/x-c'
    )
    assert list(accept) == ['text/x-c', 'text/x-dvi', 'text/plain']


# NilAccept tests

def test_nil():
    nilaccept = NilAccept()
    assert repr(nilaccept) == "<NilAccept: <class 'webob.acceptparse.Accept'>>"
    assert not nilaccept
    assert str(nilaccept) == ''
    assert nilaccept.quality('dummy') == 0

def test_nil_add():
    nilaccept = NilAccept()
    accept = Accept('text/html')
    assert nilaccept + accept is accept
    new_accept = nilaccept + nilaccept
    assert isinstance(new_accept, accept.__class__)
    assert new_accept.header_value == ''
    new_accept = nilaccept + 'foo'
    assert isinstance(new_accept, accept.__class__)
    assert new_accept.header_value == 'foo'

def test_nil_radd():
    nilaccept = NilAccept()
    accept = Accept('text/html')
    assert isinstance('foo' + nilaccept, accept.__class__)
    assert ('foo' + nilaccept).header_value == 'foo'
    # How to test ``if isinstance(item, self.MasterClass): return item``
    # under NilAccept.__radd__ ??

def test_nil_radd_masterclass():
    # Is this "reaching into" __radd__ legit?
    nilaccept = NilAccept()
    accept = Accept('text/html')
    assert nilaccept.__radd__(accept) is accept

def test_nil_contains():
    nilaccept = NilAccept()
    assert 'anything' in nilaccept

def test_nil_best_match():
    nilaccept = NilAccept()
    assert nilaccept.best_match(['foo', 'bar']) == 'foo'
    assert nilaccept.best_match([('foo', 1), ('bar', 0.5)]) == 'foo'
    assert nilaccept.best_match([('foo', 0.5), ('bar', 1)]) == 'bar'
    assert nilaccept.best_match([('foo', 0.5), 'bar']) == 'bar'
    assert nilaccept.best_match([('foo', 0.5), 'bar'],
                                default_match=True) == 'bar'
    assert nilaccept.best_match([('foo', 0.5), 'bar'],
                                default_match=False) == 'bar'
    assert nilaccept.best_match([], default_match='fallback') == 'fallback'

def test_nil_iter():
    nilaccept = NilAccept()
    assert list(nilaccept) == []


# NoAccept tests
def test_noaccept_contains():
    assert 'text/plain' not in NoAccept()


# MIMEAccept tests

def test_mime_init():
    mimeaccept = MIMEAccept('image/jpg')
    assert mimeaccept.parsed == [('image/jpg', 1)]
    mimeaccept = MIMEAccept('image/png, image/jpg;q=0.5')
    assert mimeaccept.parsed == [('image/png', 1), ('image/jpg', 0.5)]
    mimeaccept = MIMEAccept('image, image/jpg;q=0.5')
    assert mimeaccept.parsed == [('image/jpg', 0.5)]
    mimeaccept = MIMEAccept('*/*')
    assert mimeaccept.parsed == [('*/*', 1)]
    mimeaccept = MIMEAccept('*/png')
    assert mimeaccept.parsed == []
    mimeaccept = MIMEAccept('image/pn*')
    assert mimeaccept.parsed == []
    mimeaccept = MIMEAccept('imag*/png')
    assert mimeaccept.parsed == []
    mimeaccept = MIMEAccept('image/*')
    assert mimeaccept.parsed == [('image/*', 1)]

def test_accept_html():
    mimeaccept = MIMEAccept('image/jpg')
    assert not mimeaccept.accept_html()
    mimeaccept = MIMEAccept('image/jpg, text/html')
    assert mimeaccept.accept_html()

def test_match():
    mimeaccept = MIMEAccept('image/jpg')
    assert mimeaccept._match('image/jpg', 'image/jpg')
    assert mimeaccept._match('image/*', 'image/jpg')
    assert mimeaccept._match('*/*', 'image/jpg')
    assert not mimeaccept._match('text/html', 'image/jpg')

    mismatches = [
        ('B/b', 'A/a'),
        ('B/b', 'B/a'),
        ('B/b', 'A/b'),
        ('A/a', 'B/b'),
        ('B/a', 'B/b'),
        ('A/b', 'B/b')
    ]
    for mask, offer in mismatches:
        assert not mimeaccept._match(mask, offer)


def test_wildcard_matching():
    """
    Wildcard matching forces the match to take place against the type
    or subtype of the mask and offer (depending on where the wildcard
    matches)
    """
    mimeaccept = MIMEAccept('type/subtype')
    matches = [
        ('*/*', '*/*'),
        ('*/*', 'A/*'),
        ('*/*', '*/a'),
        ('*/*', 'A/a'),
        ('A/*', '*/*'),
        ('A/*', 'A/*'),
        ('A/*', '*/a'),
        ('A/*', 'A/a'),
        ('*/a', '*/*'),
        ('*/a', 'A/*'),
        ('*/a', '*/a'),
        ('*/a', 'A/a'),
        ('A/a', '*/*'),
        ('A/a', 'A/*'),
        ('A/a', '*/a'),
        ('A/a', 'A/a'),
        # Offers might not contain a subtype
        ('*/*', '*'),
        ('A/*', '*'),
        ('*/a', '*')]
    for mask, offer in matches:
        assert mimeaccept._match(mask, offer)
        # Test malformed mask and offer variants where either is missing
        # a type or subtype
        assert mimeaccept._match('A', offer)
        assert mimeaccept._match(mask, 'a')

    mismatches = [
        ('B/b', 'A/*'),
        ('B/*', 'A/a'),
        ('B/*', 'A/*'),
        ('*/b', '*/a')]
    for mask, offer in mismatches:
        assert not mimeaccept._match(mask, offer)

def test_mimeaccept_contains():
    mimeaccept = MIMEAccept('A/a, B/b, C/c')
    assert 'A/a' in mimeaccept
    assert 'A/*' in mimeaccept
    assert '*/a' in mimeaccept
    assert not 'A/b' in mimeaccept
    assert not 'B/a' in mimeaccept

def test_accept_json():
    mimeaccept = MIMEAccept('text/html, *; q=.2, */*; q=.2')
    assert mimeaccept.best_match(['application/json']) == 'application/json'

def test_accept_mixedcase():
    """3.7 Media Types
           [...]
           The type, subtype, and parameter attribute names are case-
           insensitive."""
    mimeaccept = MIMEAccept('text/HtMl')
    assert mimeaccept.accept_html()

def test_match_mixedcase():
    mimeaccept = MIMEAccept('image/jpg; q=.2, Image/pNg; Q=.4, image/*; q=.05')
    assert mimeaccept.best_match(['Image/JpG']) == 'Image/JpG'
    assert mimeaccept.best_match(['image/Tiff']) == 'image/Tiff'
    assert mimeaccept.best_match(['image/Tiff', 'image/PnG', 'image/jpg']) == 'image/PnG'

def test_match_uppercase_q():
    """The relative-quality-factor "q" parameter is defined as an exact string
       in "14.1 Accept" BNF grammar"""
    mimeaccept = MIMEAccept('image/jpg; q=.4, Image/pNg; Q=.2, image/*; q=.05')
    assert mimeaccept.parsed == [('image/jpg', 0.4), ('image/png', 1), ('image/*', 0.05)]

# property tests

def test_accept_property_fget():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, 'val')
    assert desc.fget(req).header_value == 'val'

def test_accept_property_fget_nil():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/')
    assert type(desc.fget(req)) == NilAccept

def test_accept_property_fset():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, 'baz')
    assert desc.fget(req).header_value == 'baz'

def test_accept_property_fset_acceptclass():
    req = Request.blank('/', environ={'envkey': 'envval'})
    req.accept_charset = ['utf-8', 'latin-11']
    assert req.accept_charset.header_value == 'utf-8, latin-11, iso-8859-1'

def test_accept_property_fdel():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, 'val')
    assert desc.fget(req).header_value == 'val'
    desc.fdel(req)
    assert type(desc.fget(req)) == NilAccept


class TestAcceptLanguage(object):
    @pytest.mark.parametrize('value', [
        '',
        '*s',
        '*-a',
        'a-*',
        'a' * 9,
        'a-' + 'a' * 9,
        'a-a-' + 'a' * 9,
        '-',
        'a-',
        '-a',
        '---',
        '--a',
        '1-a',
        '1-a-a',
        'en_gb',
        'en/gb',
        'foo, bar, baz;q= 0.001',
        'foo , ,bar,charlie   ',
    ])
    def test_parse__invalid_header(self, value):
        with pytest.raises(ValueError):
            AcceptLanguage.parse(value=value)

    @pytest.mark.parametrize('value, expected_list', [
        ('*', [('*', 1.0)]),
        ('fR;q=0.5', [('fR', 0.5)]),
        ('zh-Hant;q=0.500', [('zh-Hant', 0.5)]),
        ('zh-Hans-CN;q=1', [('zh-Hans-CN', 1.0)]),
        ('de-CH-x-phonebk;q=1.0', [('de-CH-x-phonebk', 1.0)]),
        ('az-Arab-x-AZE-derbend;q=1.00', [('az-Arab-x-AZE-derbend', 1.0)]),
        ('zh-CN-a-myExt-x-private;q=1.000', [('zh-CN-a-myExt-x-private', 1.0)]),
        ('aaaaaaaa', [('aaaaaaaa', 1.0)]),
        ('aaaaaaaa-a', [('aaaaaaaa-a', 1.0)]),
        ('aaaaaaaa-aaaaaaaa', [('aaaaaaaa-aaaaaaaa', 1.0)]),
        ('a-aaaaaaaa-aaaaaaaa', [('a-aaaaaaaa-aaaaaaaa', 1.0)]),
        ('aaaaaaaa-a-aaaaaaaa', [('aaaaaaaa-a-aaaaaaaa', 1.0)]),
        (
            'zh-Hant;q=0.372,zh-CN-a-myExt-x-private;q=0.977,de,*;q=0.000',
            [
                ('zh-Hant', 0.372), ('zh-CN-a-myExt-x-private', 0.977),
                ('de', 1.0), ('*', 0.0)
            ]
        ),
        (
            ',\t foo \t;\t q=0.345,, bar ; Q=0.456 \t,  ,\tcharlie \t,,  ,',
            [('foo', 0.345), ('bar', 0.456), ('charlie', 1.0)]
        ),
        # RFC 7230 Section 7
        ('foo,bar', [('foo', 1.0), ('bar', 1.0)]),
        ('foo, bar,', [('foo', 1.0), ('bar', 1.0)]),
        # RFC 7230 Errata ID: 4169
        ('foo , ,bar,charlie', [('foo', 1.0), ('bar', 1.0), ('charlie', 1.0)]),
    ])
    def test_parse__valid_header(self, value, expected_list):
        returned = AcceptLanguage.parse(value=value)
        list_of_returned = list(returned)
        assert list_of_returned == expected_list


class TestAcceptLanguageValidHeader(object):
    @pytest.mark.parametrize('header_value', [
        '',
        ', da;q=0.2, en-gb;q=0.3 ',
    ])
    def test___init___invalid_header(self, header_value):
        with pytest.raises(ValueError):
            AcceptLanguageValidHeader(header_value=header_value)

    def test___init___valid_header(self):
        header_value = \
            'zh-Hant;q=0.372,zh-CN-a-myExt-x-private;q=0.977,de,*;q=0.000'
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed == [
            ('zh-Hant', 0.372), ('zh-CN-a-myExt-x-private', 0.977),
            ('de', 1.0), ('*', 0.0)
        ]
        assert instance._parsed_nonzero == [
            ('zh-Hant', 0.372), ('zh-CN-a-myExt-x-private', 0.977),
            ('de', 1.0)
        ]
        assert isinstance(instance, AcceptLanguage)

    def test___add___None(self):
        left_operand = AcceptLanguageValidHeader(header_value='en')
        result = left_operand + None
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('right_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
        ',',
        [','],
        (',',),
        {',': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptLanguageValidHeader(header_value='en')
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('str_', ['', 'en_gb', ','])
    def test___add___other_type_with_invalid___str__(self, str_,):
        left_operand = AcceptLanguageValidHeader(header_value='en')
        class Other(object):
            def __str__(self):
                return str_
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test___add___valid_value(self, value, value_as_header):
        header = ',\t ,de, zh-Hans;q=0.333,'
        result = AcceptLanguageValidHeader(header_value=header) + value
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == header + ', ' + value_as_header

    def test___add___other_type_with_valid___str__(self):
        header = ',\t ,de, zh-Hans;q=0.333,'
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        right_operand = Other()
        result = AcceptLanguageValidHeader(header_value=header) + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == header + ', ' + str(right_operand)

    def test___add___AcceptLanguageValidHeader(self):
        header1 = ',\t ,de, zh-Hans;q=0.333,'
        header2 = ', ,fr;q=0, \tes;q=1,'
        result = AcceptLanguageValidHeader(header_value=header1) + \
            AcceptLanguageValidHeader(header_value=header2)
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == header1 + ', ' + header2

    def test___add___AcceptLanguageNoHeader(self):
        valid_header_instance = AcceptLanguageValidHeader(header_value='es')
        result = valid_header_instance + AcceptLanguageNoHeader()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    @pytest.mark.parametrize('header_value', ['', 'en_gb', ','])
    def test___add___AcceptLanguageInvalidHeader(self, header_value):
        valid_header_instance = AcceptLanguageValidHeader(
            header_value='header',
        )
        result = valid_header_instance + AcceptLanguageInvalidHeader(
            header_value=header_value,
        )
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    def test___radd___None(self):
        right_operand = AcceptLanguageValidHeader(header_value='en')
        result = None + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('left_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
        ',',
        [','],
        (',',),
        {',': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptLanguageValidHeader(header_value='en')
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('str_', ['', 'en_gb', ','])
    def test___radd___other_type_with_invalid___str__(self, str_,):
        right_operand = AcceptLanguageValidHeader(header_value='en')
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test___radd___valid_value(self, value, value_as_header):
        right_operand = AcceptLanguageValidHeader(
            header_value=',\t ,de, zh-Hans;q=0.333,',
        )
        result = value + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == value_as_header + ', ' + \
            right_operand.header_value

    def test___radd___other_type_with_valid___str__(self):
        right_operand = AcceptLanguageValidHeader(
            header_value=',\t ,de, zh-Hans;q=0.333,',
        )
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        left_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == str(left_operand) + ', ' + \
            right_operand.header_value

    def test___bool__(self):
        instance = AcceptLanguageValidHeader(header_value='valid-header')
        returned = bool(instance)
        assert returned is True

    @pytest.mark.parametrize('header_value, offer', [
        ('*', 'da'),
        ('da', 'DA'),
        ('en', 'en-gb'),
        ('en-gb', 'en-gb'),
        ('en-gb', 'en'),
        ('en-gb', 'en_GB'),
    ])
    def test___contains___in(self, header_value, offer):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert offer in instance

    @pytest.mark.parametrize('header_value, offer', [
        ('en-gb', 'en-us'),
        ('en-gb', 'fr-fr'),
        ('en-gb', 'fr'),
        ('en', 'fr-fr'),
    ])
    def test___contains___not_in(self, header_value, offer):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert offer not in instance

    @pytest.mark.parametrize('header_value, expected_list', [
        ('fr;q=0, jp;q=0', []),
        ('en-gb, da', ['en-gb', 'da']),
        ('en-gb;q=0.5, da;q=0.5', ['en-gb', 'da']),
        (
            'de;q=0.8, de-DE-1996;q=0.5, de-Deva;q=0, de-Latn-DE',
            ['de-Latn-DE', 'de', 'de-DE-1996']
        ),
        # __iter__ is currently a simple filter for the ranges in the header
        # with non-0 qvalues, and does not attempt to account for the special
        # meanings of q=0 and *:
        ('en-gb;q=0, *', ['*']),
        ('de, de;q=0', ['de']),
    ])
    def test___iter__(self, header_value, expected_list):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert list(instance) == expected_list

    def test___repr__(self):
        instance = AcceptLanguageValidHeader(
            header_value=',da;q=0.200,en-gb;q=0.300',
        )
        assert repr(instance) == \
            "<AcceptLanguageValidHeader ('da;q=0.2, en-gb;q=0.3')>"

    def test___str__(self):
        header_value = \
            ', \t,de;q=0.000 \t, es;q=1.000, zh, jp;q=0.210  ,'
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert str(instance) == 'de;q=0, es, zh, jp;q=0.21'

    @pytest.mark.parametrize(
        'header_value, language_tags, expected_returned',
        [
            # Example from RFC 4647, Section 3.4
            (
                'de-de',
                ['de', 'de-DE-1996', 'de-Deva', 'de-Latn-DE'],
                [('de-DE-1996', 1.0)]
            ),
            # Empty `language_tags`
            (
                'a',
                [],
                []
            ),
            # No matches
            (
                'a, b',
                ['c', 'd'],
                []
            ),
            # Several ranges and tags, no matches
            (
                'a-b;q=0.9, c-d;q=0.5, e-f',
                ('a', 'b', 'c', 'd', 'e', 'f'),
                []
            ),
            # Case-insensitive match
            (
                'foO, BaR',
                ['foo', 'bar'],
                [('foo', 1.0), ('bar', 1.0)]
            ),
            # If a tag matches a non-'*' range with q=0, tag is filtered out
            (
                'b;q=1, b;q=0, a, b-c, d;q=0',
                ['b-c', 'a', 'b-c-d', 'd-e-f'],
                [('a', 1.0)]
            ),
            # Match if a range exactly equals a tag
            (
                'd-e-f',
                ['a-b-c', 'd-e-f'],
                [('d-e-f', 1.0)]
            ),
            # Match if a range exactly equals a prefix of the tag such that the
            # first character following the prefix is '-'
            (
                'a-b-c-d, a-b-c-d-e, a-b-c-d-f-g-h',
                ['a-b-c-d-f-g'],
                [('a-b-c-d-f-g', 1.0)]
            ),
            # If a tag matches a '*' range with q=0, the tag is filtered out
            # (and any other '*' ranges with non-0 qvalues have no effect)
            (
                'a, b, *;q=0.5, *;q=0',
                ['a-a', 'b-a', 'c-a'],
                [('a-a', 1.0), ('b-a', 1.0)]
            ),
            # '*', when it is the only range in the header, matches everything
            (
                '*',
                ['a', 'b'],
                [('a', 1.0), ('b', 1.0)]
            ),
            # '*' range matches only tags not matched by any other range
            (
                '*;q=0.2, a;q=0.5, b',
                ['a-a', 'b-a', 'c-a', 'd-a'],
                [('b-a', 1.0), ('a-a', 0.5), ('c-a', 0.2), ('d-a', 0.2)]
            ),
            # '*' range without a qvalue gives a matched qvalue of 1.0
            (
                'a;q=0.5, b, *',
                ['a-a', 'b-a', 'c-a', 'd-a'],
                [('b-a', 1.0), ('c-a', 1.0), ('d-a', 1.0), ('a-a', 0.5)]
            ),
            # The qvalue for the '*' range works the same way as qvalues for
            # non-'*' ranges.
            (
                'a;q=0.5, *;q=0.9',
                # (meaning: prefer anything other than 'a', with 'a' as a
                # fallback)
                ['a', 'b'],
                [('b', 0.9), ('a', 0.5)]
            ),
            # When there is more than one '*' range in the header, the one with
            # the highest qvalue is matched
            (
                'a;q=0.5, *;q=0.6, b;q=0.7, *;q=0.9',
                ['a', 'b', 'c'],
                [('c', 0.9), ('b', 0.7), ('a', 0.5)]
            ),
            # When there is more than one '*' range in the header, and they
            # have the same qvalue, the one that appears earlier in the header
            # is matched
            (
                'a;q=0.5, *;q=0.9, b;q=0.9, *;q=0.9',
                ['a', 'b', 'c'],
                [('c', 0.9), ('b', 0.9), ('a', 0.5)]
            ),
            # More than one range matching the same tag: range with the highest
            # qvalue is matched
            (
                'a-b-c;q=0.7, a;q=0.9, a-b;q=0.8',
                ['a-b-c'],
                [('a-b-c', 0.9)]
            ),
            # More than one range with the same qvalue matching the same tag:
            # the range in an earlier position in the header is matched
            (
                'a-b-c;q=0.7, a;q=0.9, b;q=0.9, a-b;q=0.9',
                ['a-b-c', 'b'],
                [('a-b-c', 0.9), ('b', 0.9)]
            ),
            # The returned list of tuples is sorted in descending order of qvalue
            (
                'a;q=0.7, b;q=0.3, c, d;q=0.5',
                ['d', 'c', 'b', 'a'],
                [('c', 1.0), ('a', 0.7), ('d', 0.5), ('b', 0.3)]
            ),
            # When qvalues are the same, the tag whose matched range appears
            # earlier in the header comes first
            (
                'a, c, b',
                ['b', 'a', 'c'],
                [('a', 1.0), ('c', 1.0), ('b', 1.0)]
            ),
            # When many tags match the same range (so same qvalue and same
            # matched range position in header), they are returned in order of
            # their position in the `language_tags` argument
            (
                'a',
                ['a-b', 'a', 'a-b-c'],
                [('a-b', 1.0), ('a', 1.0), ('a-b-c', 1.0)]
            ),
        ]
    )
    def test_basic_filtering(
            self, header_value, language_tags, expected_returned,
        ):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.basic_filtering(language_tags=language_tags)
        assert returned == expected_returned

    @pytest.mark.parametrize(
        'header_value, offers, default_match, expected_returned', [
            ('bar, *;q=0', ['foo'], None, None),
            ('en-gb, sr-Cyrl', ['sr-Cyrl', 'en-gb'], None, 'sr-Cyrl'),
            ('en-gb, sr-Cyrl', ['en-gb', 'sr-Cyrl'], None, 'en-gb'),
            ('en-gb, sr-Cyrl', [('sr-Cyrl', 0.5), 'en-gb'], None, 'en-gb'),
            (
                'en-gb, sr-Cyrl', [('sr-Cyrl', 0.5), ('en-gb', 0.4)], None,
                'sr-Cyrl',
            ),
            ('en-gb, sr-Cyrl;q=0.5', ['en-gb', 'sr-Cyrl'], None, 'en-gb'),
            ('en-gb;q=0.5, sr-Cyrl', ['en-gb', 'sr-Cyrl'], None, 'sr-Cyrl'),
            (
                'en-gb, sr-Cyrl;q=0.55, es;q=0.59', ['en-gb', 'sr-Cyrl'], None,
                'en-gb',
            ),
            (
                'en-gb;q=0.5, sr-Cyrl;q=0.586, es-419;q=0.597',
                ['en-gb', 'es-419'], None, 'es-419',
            ),
        ]
    )
    def test_best_match(
        self, header_value, offers, default_match, expected_returned,
    ):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.best_match(
            offers=offers, default_match=default_match,
        )
        assert returned == expected_returned

    def test_lookup_default_tag_and_default_cannot_both_be_None(self):
        instance = AcceptLanguageValidHeader(header_value='valid-header')
        with pytest.raises(TypeError):
            instance.lookup(
                language_tags=['tag'],
                default_range='language-range',
                default_tag=None,
                default=None,
            )

    def test_lookup_default_range_cannot_be_asterisk(self):
        instance = AcceptLanguageValidHeader(header_value='valid-header')
        with pytest.raises(ValueError):
            instance.lookup(
                language_tags=['tag'],
                default_range='*',
                default_tag='default-tag',
                default=None,
            )

    @pytest.mark.parametrize(
        (
            'header_value, language_tags, default_range, default_tag, default'
            ', expected'
        ),
        [
            # Each language range in the header is considered in turn, in
            # descending order of qvalue
            (
                'aA;q=0.3, Bb, cC;q=0.7',
                ['Aa', 'bB', 'Cc'],
                None, 'default-tag', None,
                'bB',
            ),
            # For ranges with the same qvalue, position in header is the
            # tiebreaker.
            (
                'bB-Cc;q=0.8, aA;q=0.9, Bb;q=0.9',
                ['bb', 'aa'],
                None, 'default-tag', None,
                'aa',
            ),
            # Each language range represents the most specific tag that is an
            # acceptable match. Examples from RFC 4647, section 3.4, first
            # paragraph:
            (
                'de-ch',
                ['de-CH-1996', 'de-CH', 'de'],
                None, 'default-tag', None,
                'de-CH',
            ),
            (
                'de-ch',
                ['de-CH-1996', 'de'],
                None, 'default-tag', None,
                'de',
            ),
            # The language range is progressively truncated from the end until
            # a matching language tag is located. From the example of a Lookup
            # Fallback Pattern in RFC 4647, section 3.4:
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant-CN-x-private1-private2',
                    'zh-Hant-CN-x-private1',
                    'zh-Hant-CN-x',
                    'zh-Hant-CN',
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant-CN-x-private1-private2',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant-CN-x-private1',
                    'zh-Hant-CN-x',
                    'zh-Hant-CN',
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant-CN-x-private1',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant-CN-x',
                    'zh-Hant-CN',
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant-CN',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant-CN',
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant-CN',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                ['zh'],
                None, 'default-tag', None,
                'zh',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                ['some-other-tag-1', 'some-other-tag-2'],
                None, 'default-tag', None,
                'default-tag',
            ),
            # Further tests to check that single-letter or -digit subtags are
            # removed at the same time as their closest trailing subtag:
            (
                'AA-T-subtag',
                ['Aa-t', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            (
                'AA-1-subtag',
                ['aa-1', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            (
                'Aa-P-subtag-8-subtag',
                ['Aa-p-subtag-8', 'Aa-p', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            (
                'aA-3-subTag-C-subtag',
                ['aA-3-subtag-c', 'aA-3', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            # Test that single-letter or -digit subtag in first position works
            # as expected
            (
                'T-subtag',
                ['t-SubTag', 'another'],
                None, 'default-tag', None,
                't-SubTag',
            ),
            (
                'T-subtag',
                ['another'],
                None, 'default-tag', None,
                'default-tag',
            ),
            # If the language range "*" is followed by other language ranges,
            # it is skipped.
            (
                '*, Aa-aA-AA',
                ['bb', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            # If the language range "*" is the only one in the header, lookup
            # proceeds to the default arguments.
            (
                '*',
                ['bb', 'aa'],
                None, 'default-tag', None,
                'default-tag',
            ),
            # If no other language range follows the "*" in the header, lookup
            # proceeds to the default arguments.
            (
                'dd, cc, *',
                ['bb', 'aa'],
                None, 'default-tag', None,
                'default-tag',
            ),
            # If a non-'*' range has q=0, any tag that matches the range
            # exactly (without subtag truncation) is not acceptable.
            (
                'aa, bB-Cc-DD;q=0, bB-Cc, cc',
                ['bb', 'bb-Cc-DD', 'bb-cC-dd', 'Bb-cc', 'bb-cC-dd'],
                None, 'default-tag', None,
                'Bb-cc',
            ),
            # ;q=0 and ;q={not 0} both in header: q=0 takes precedence and
            # makes the exact match not acceptable, but the q={not 0} means
            # that tags can still match after subtag truncation.
            (
                'aa, bB-Cc-DD;q=0.9, cc, Bb-cC-dD;q=0',
                ['bb', 'Bb-Cc', 'Bb-cC-dD'],
                None, 'default-tag', None,
                'Bb-Cc',
            ),
            # If none of the ranges in the header match any of the language
            # tags, and the `default_range` argument is not None and does not
            # match any q=0 range in the header, we search through it by
            # progressively truncating from the end, as we do with the ranges
            # in the header. Example from RFC 4647, section 3.4.1:
            (
                'fr-FR, zh-Hant',
                [
                    'fr-FR',
                    'fr',
                    'zh-Hant',
                    'zh',
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'fr-FR',
            ),
            (
                'fr-FR, zh-Hant',
                [
                    'fr',
                    'zh-Hant',
                    'zh',
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'fr',
            ),
            (
                'fr-FR, zh-Hant',
                [
                    'zh-Hant',
                    'zh',
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'zh-Hant',
            ),
            (
                'fr-FR, zh-Hant',
                [
                    'zh',
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'zh',
            ),
            (
                'fr-FR, zh-Hant',
                [
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'ja-JP',
            ),
            (
                'fr-FR, zh-Hant',
                ['ja'],
                'ja-JP', 'default-tag', None,
                'ja',
            ),
            (
                'fr-FR, zh-Hant',
                ['some-other-tag-1', 'some-other-tag-2'],
                'ja-JP', 'default-tag', None,
                'default-tag',
            ),
            # If none of the ranges in the header match the language tags, the
            # `default_range` argument is not None, and there is a '*;q=0'
            # range in the header, then the `default_range` and its substrings
            # from subtag truncation are not acceptable.
            (
                'aa-bb, cc-dd, *;q=0',
                ['ee-ff', 'ee'],
                'ee-ff', None, 'default',
                'default',
            ),
            # If none of the ranges in the header match the language tags, the
            # `default_range` argument is not None, and the argument exactly
            # matches a non-'*' range in the header with q=0 (without fallback
            # subtag truncation), then the `default_range` itself is not
            # acceptable...
            (
                'aa-bb, cc-dd, eE-Ff;q=0',
                ['Ee-fF'],
                'EE-FF', 'default-tag', None,
                'default-tag',
            ),
            # ...but it should still be searched with subtag truncation,
            # because its substrings other than itself are still acceptable:
            (
                'aa-bb, cc-dd, eE-Ff-Gg;q=0',
                ['Ee', 'Ee-fF-gG', 'Ee-fF'],
                'EE-FF-GG', 'default-tag', None,
                'Ee-fF',
            ),
            (
                'aa-bb, cc-dd, eE-Ff-Gg;q=0',
                ['Ee-fF-gG', 'Ee'],
                'EE-FF-GG', 'default-tag', None,
                'Ee',
            ),
            # If `default_range` only has one subtag, then no subtag truncation
            # is possible, and we proceed to `default-tag`:
            (
                'aa-bb, cc-dd, eE;q=0',
                ['Ee'],
                'EE', 'default-tag', None,
                'default-tag',
            ),
            # If the `default_range` argument would only match a non-'*' range
            # in the header with q=0 exactly if the `default_range` had subtags
            # from the end truncated, then it is acceptable, and we attempt to
            # match it with the language tags using subtag truncation. However,
            # the tag equivalent of the range with q=0 would be considered not
            # acceptable and ruled out, if we reach it during the subtag
            # truncation search.
            (
                'aa-bb, cc-dd, eE-Ff;q=0',
                ['Ee-fF', 'Ee-fF-33', 'ee'],
                'EE-FF-33', 'default-tag', None,
                'Ee-fF-33',
            ),
            (
                'aa-bb, cc-dd, eE-Ff;q=0',
                ['Ee-fF', 'eE'],
                'EE-FF-33', 'default-tag', None,
                'eE',
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, and the `default_tag`
            # argument is not None and does not match any range in the header
            # with q=0, then the `default_tag` argument is returned.
            (
                'aa-bb, cc-dd',
                ['ee-ff', 'ee'],
                None, 'default-tag', None,
                'default-tag',
            ),
            (
                'aa-bb, cc-dd',
                ['ee-ff', 'ee'],
                'gg-hh', 'default-tag', None,
                'default-tag',
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, the `default_tag` argument is
            # not None, and there is a '*' range in the header with q=0, then
            # the `default_tag` argument is not acceptable.
            (
                'aa-bb, cc-dd, *;q=0',
                ['ee-ff', 'ee'],
                'gg-hh', 'ii-jj', 'default',
                'default',
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, the `default_tag` argument is
            # not None and matches a non-'*' range in the header with q=0
            # exactly, then the `default_tag` argument is not acceptable.
            (
                'aa-bb, cc-dd, iI-jJ;q=0',
                ['ee-ff', 'ee'],
                'gg-hh', 'Ii-Jj', 'default',
                'default',
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, and the `default_tag`
            # argument is None, then we proceed to the `default` argument.
            (
                'aa-bb, cc-dd',
                ['ee-ff', 'ee'],
                None, None, 'default',
                'default',
            ),
            (
                'aa-bb, cc-dd',
                ['ee-ff', 'ee'],
                'gg-hh', None, 'default',
                'default',
            ),
            # If we fall back to the `default` argument, and it is not a
            # callable, the argument itself is returned.
            (
                'aa',
                ['bb'],
                None, None, 0,
                0,
            ),
            (
                'Aa, cC;q=0',
                ['bb'],
                'aA-Cc', 'Cc', ['non-callable object'],
                ['non-callable object'],
            ),
            # If we fall back to the `default` argument, and it is a callable,
            # it is called, and the callable's return value is returned by the
            # method.
            (
                'aa',
                ['bb'],
                None, None, lambda: 'callable called',
                'callable called',
            ),
            (
                'Aa, cc;q=0',
                ['bb'],
                'aA-cC', 'cc', lambda: 'callable called',
                'callable called',
            ),
            # Even if the 'default' argument is a str that matches a q=0 range
            # in the header, it is still returned.
            (
                'aa, *;q=0',
                ['bb'],
                None, None, 'cc',
                'cc',
            ),
            (
                'aa, cc;q=0',
                ['bb'],
                None, None, 'cc',
                'cc',
            ),
            # If the `default_tag` argument is not acceptable because of a q=0
            # range in the header, and the `default` argument is None, then
            # None is returned.
            (
                'aa, Bb;q=0',
                ['cc'],
                None, 'bB', None,
                None,
            ),
            (
                'aa, *;q=0',
                ['cc'],
                None, 'bb', None,
                None,
            ),
            # Test that method works with empty `language_tags`:
            (
                'range',
                [],
                None, 'default-tag', None,
                'default-tag',
            ),
            # Test that method works with empty `default_range`:
            (
                'range',
                [],
                '', 'default-tag', None,
                'default-tag',
            ),
            (
                'range',
                ['tag'],
                '', 'default-tag', None,
                'default-tag',
            ),
            # Test that method works with empty `default_tag`:
            (
                'range',
                [],
                '', '', None,
                '',
            ),
            (
                'range',
                ['tag'],
                'default-range', '', None,
                '',
            ),
        ]
    )
    def test_lookup(
            self, header_value, language_tags, default_range, default_tag,
            default, expected,
        ):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.lookup(
            language_tags=language_tags,
            default_range=default_range,
            default_tag=default_tag,
            default=default,
        )
        assert returned == expected

    @pytest.mark.parametrize('header_value, offer, expected_returned', [
        ('en-gb', 'en-gb', 1),
        ('en-gb;q=0.5', 'en-gb', 0.5),
        ('en-gb', 'sr-Cyrl', None),
    ])
    def test_quality(self, header_value, offer, expected_returned):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.quality(offer=offer)
        assert returned == expected_returned


class TestAcceptLanguageNoHeader(object):
    def test___init__(self):
        instance = AcceptLanguageNoHeader()
        assert instance.header_value is None
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, AcceptLanguage)

    def test___add___None(self):
        instance = AcceptLanguageNoHeader()
        result = instance + None
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not instance

    @pytest.mark.parametrize('right_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptLanguageNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand

    @pytest.mark.parametrize('str_', ['', 'en_gb'])
    def test___add___other_type_with_invalid___str__(self, str_,):
        left_operand = AcceptLanguageNoHeader()
        class Other(object):
            def __str__(self):
                return str_
        result = left_operand + Other()
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test___add___valid_value(self, value, value_as_header):
        result = AcceptLanguageNoHeader() + value
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == value_as_header

    def test___add___other_type_with_valid___str__(self):
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        right_operand = Other()
        result = AcceptLanguageNoHeader() + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == str(right_operand)

    def test___add___AcceptLanguageValidHeader(self):
        right_operand = AcceptLanguageValidHeader(
            header_value=', ,fr;q=0, \tes;q=1,',
        )
        result = AcceptLanguageNoHeader() + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value

    def test___add___AcceptLanguageNoHeader(self):
        left_operand = AcceptLanguageNoHeader()
        right_operand = AcceptLanguageNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand
        assert result is not right_operand

    @pytest.mark.parametrize('invalid_header_value', ['', 'en_gb'])
    def test___add___AcceptLanguageInvalidHeader(self, invalid_header_value):
        left_operand = AcceptLanguageNoHeader()
        result = left_operand + AcceptLanguageInvalidHeader(
            header_value=invalid_header_value,
        )
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand

    def test___bool__(self):
        instance = AcceptLanguageNoHeader()
        returned = bool(instance)
        assert returned is False

    def test___contains__(self):
        instance = AcceptLanguageNoHeader()
        returned = ('any-tag' in instance)
        assert returned is True

    def test___iter__(self):
        instance = AcceptLanguageNoHeader()
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        right_operand = AcceptLanguageNoHeader()
        result = None + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('left_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptLanguageNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('str_', ['', 'en_gb', ','])
    def test___radd___other_type_with_invalid___str__(self, str_,):
        right_operand = AcceptLanguageNoHeader()
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test___radd___valid_value(self, value, value_as_header):
        result = value + AcceptLanguageNoHeader()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == value_as_header

    def test___radd___other_type_with_valid___str__(self):
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        left_operand = Other()
        result = left_operand + AcceptLanguageNoHeader()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == str(left_operand)

    def test___repr__(self):
        instance = AcceptLanguageNoHeader()
        assert repr(instance) == '<AcceptLanguageNoHeader>'

    def test___str__(self):
        instance = AcceptLanguageNoHeader()
        assert str(instance) == '<no header in request>'

    def test_basic_filtering(self):
        instance = AcceptLanguageNoHeader()
        returned = instance.basic_filtering(language_tags=['tag1', 'tag2'])
        assert returned == []

    @pytest.mark.parametrize('offers, default_match, expected_returned', [
        (['foo', 'bar'], None, 'foo'),
        ([('foo', 1), ('bar', 0.5)], None, 'foo'),
        ([('foo', 0.5), ('bar', 1)], None, 'bar'),
        ([('foo', 0.5), 'bar'], None, 'bar'),
        ([('foo', 0.5), 'bar'], object(), 'bar'),
        ([], 'fallback', 'fallback'),
    ])
    def test_best_match(self, offers, default_match, expected_returned):
        instance = AcceptLanguageNoHeader()
        returned = instance.best_match(
            offers=offers, default_match=default_match,
        )
        assert returned == expected_returned

    def test_lookup_default_tag_and_default_cannot_both_be_None(self):
        instance = AcceptLanguageNoHeader()
        with pytest.raises(TypeError):
            instance.lookup(default_tag=None, default=None)

    @pytest.mark.parametrize('default_tag, default, expected', [
        # If `default_tag` is not None, it is returned.
        ('default-tag', 'default', 'default-tag'),
        # If `default_tag` is None, we proceed to the `default` argument. If
        # `default` is not a callable, the argument itself is returned.
        (None, 0, 0),
        # If `default` is a callable, it is called, and the callable's return
        # value is returned by the method.
        (None, lambda: 'callable called', 'callable called'),
    ])
    def test_lookup(self, default_tag, default, expected):
        instance = AcceptLanguageNoHeader()
        returned = instance.lookup(
            default_tag=default_tag,
            default=default,
        )
        assert returned == expected

    def test_quality(self):
        instance = AcceptLanguageNoHeader()
        returned = instance.quality(offer='any-tag')
        assert returned == 1.0


class TestAcceptLanguageInvalidHeader(object):
    def test___init__(self):
        header_value = 'invalid header'
        instance = AcceptLanguageInvalidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, AcceptLanguage)

    def test___add___None(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        result = instance + None
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('right_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        result = AcceptLanguageInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('str_', ['', 'en_gb'])
    def test___add___other_type_with_invalid___str__(self, str_):
        class Other(object):
            def __str__(self):
                return str_
        result = AcceptLanguageInvalidHeader(header_value='') + Other()
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('value', [
        'en',
        ['en'],
        ('en',),
        {'en': 1.0},
    ])
    def test___add___valid_header_value(self, value):
        result = AcceptLanguageInvalidHeader(header_value='') + value
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == 'en'

    def test___add___other_type_valid_header_value(self):
        class Other(object):
            def __str__(self):
                return 'en'
        result = AcceptLanguageInvalidHeader(header_value='') + Other()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == 'en'

    def test___add___AcceptLanguageValidHeader(self):
        right_operand = AcceptLanguageValidHeader(header_value='en')
        result = AcceptLanguageInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___add___AcceptLanguageNoHeader(self):
        right_operand = AcceptLanguageNoHeader()
        result = AcceptLanguageInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    def test___add___AcceptLanguageInvalidHeader(self):
        result = AcceptLanguageInvalidHeader(header_value='') + \
            AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageNoHeader)

    def test___bool__(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = bool(instance)
        assert returned is False

    def test___contains__(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = ('any-tag' in instance)
        assert returned is True

    def test___iter__(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        result = None + instance
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('left_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        result = left_operand + AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('str_', ['', 'en_gb'])
    def test___radd___other_type_with_invalid___str__(self, str_):
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('value', [
        'en',
        ['en'],
        ('en',),
        {'en': 1.0},
    ])
    def test___radd___valid_header_value(self, value):
        result = value + AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == 'en'

    def test___radd___other_type_valid_header_value(self):
        class Other(object):
            def __str__(self):
                return 'en'
        result = Other() + AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == 'en'

    def test___repr__(self):
        instance = AcceptLanguageInvalidHeader(header_value='\x00')
        assert repr(instance) == '<AcceptLanguageInvalidHeader>'

    def test___str__(self):
        instance = AcceptLanguageInvalidHeader(header_value="invalid header")
        assert str(instance) == '<invalid header value>'

    def test_basic_filtering(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = instance.basic_filtering(language_tags=['tag1', 'tag2'])
        assert returned == []

    @pytest.mark.parametrize('offers, default_match, expected_returned', [
        (['foo', 'bar'], None, 'foo'),
        ([('foo', 1), ('bar', 0.5)], None, 'foo'),
        ([('foo', 0.5), ('bar', 1)], None, 'bar'),
        ([('foo', 0.5), 'bar'], None, 'bar'),
        ([('foo', 0.5), 'bar'], object(), 'bar'),
        ([], 'fallback', 'fallback'),
    ])
    def test_best_match(self, offers, default_match, expected_returned):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = instance.best_match(
            offers=offers, default_match=default_match,
        )
        assert returned == expected_returned

    def test_lookup_default_tag_and_default_cannot_both_be_None(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        with pytest.raises(TypeError):
            instance.lookup(default_tag=None, default=None)

    @pytest.mark.parametrize('default_tag, default, expected', [
        # If `default_tag` is not None, it is returned.
        ('default-tag', 'default', 'default-tag'),
        # If `default_tag` is None, we proceed to the `default` argument. If
        # `default` is not a callable, the argument itself is returned.
        (None, 0, 0),
        # If `default` is a callable, it is called, and the callable's return
        # value is returned by the method.
        (None, lambda: 'callable called', 'callable called'),
    ])
    def test_lookup(self, default_tag, default, expected):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = instance.lookup(
            default_tag=default_tag,
            default=default,
        )
        assert returned == expected

    def test_quality(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = instance.quality(offer='any-tag')
        assert returned == 1.0


class TestCreateAcceptLanguageHeader(object):
    def test_header_value_is_None(self):
        header_value = None
        returned = create_accept_language_header(header_value=header_value)
        assert isinstance(returned, AcceptLanguageNoHeader)
        assert returned.header_value == header_value

    def test_header_value_is_valid(self):
        header_value = 'es, ja'
        returned = create_accept_language_header(header_value=header_value)
        assert isinstance(returned, AcceptLanguageValidHeader)
        assert returned.header_value == header_value

    @pytest.mark.parametrize('header_value', ['', 'en_gb'])
    def test_header_value_is_invalid(self, header_value):
        returned = create_accept_language_header(header_value=header_value)
        assert isinstance(returned, AcceptLanguageInvalidHeader)
        assert returned.header_value == header_value


class TestAcceptLanguageProperty(object):
    def test_fget_header_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': None})
        property_ = accept_language_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptLanguageNoHeader)

    def test_fget_header_is_valid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptLanguageValidHeader)

    def test_fget_header_is_invalid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'en_gb'})
        property_ = accept_language_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptLanguageInvalidHeader)

    def test_fset_value_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        property_.fset(request=request, value=None)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert 'HTTP_ACCEPT_LANGUAGE' not in request.environ

    def test_fset_value_is_invalid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        property_.fset(request=request, value='en_GB')
        assert isinstance(request.accept_language, AcceptLanguageInvalidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == 'en_GB'

    def test_fset_value_is_valid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        property_.fset(request=request, value='en-GB')
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == 'en-GB'

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test_fset_value_types(self, value, value_as_header):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': ''})
        property_ = accept_language_property()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == value_as_header

    def test_fset_other_type_with_valid___str__(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': ''})
        property_ = accept_language_property()
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        value = Other()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == str(value)

    def test_fset_AcceptLanguageNoHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'en'})
        property_ = accept_language_property()
        header = AcceptLanguageNoHeader()
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert 'HTTP_ACCEPT_LANGUAGE' not in request.environ

    def test_fset_AcceptLanguageValidHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': ''})
        property_ = accept_language_property()
        header = AcceptLanguageValidHeader('es')
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == header.header_value

    def test_fset_AcceptLanguageInvalidHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': ''})
        property_ = accept_language_property()
        header = AcceptLanguageInvalidHeader('en_gb')
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_language, AcceptLanguageInvalidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == header.header_value

    def test_fdel_header_key_in_environ(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert 'HTTP_ACCEPT_LANGUAGE' not in request.environ

    def test_fdel_header_key_not_in_environ(self):
        request = Request.blank('/')
        property_ = accept_language_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert 'HTTP_ACCEPT_LANGUAGE' not in request.environ
