"""
file: tokenisers.py

author: Yoann Dupont

MIT License

Copyright (c) 2018 Yoann Dupont

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import re

from semtokenizers import Span
from semtokenizers.constants import url_re, email_re


__spaces = re.compile(r"\s+", re.U + re.M)
__dots = re.compile(r"(\.{2,})$")
__cls = re.compile(r"(-je|-tu|-nous|-vous|(:?-t)?-(:?on|ils?|elles?))\b", re.U + re.I)
__is_abn = re.compile(r"\b(dr|me?lles?|mme?s?|mr?s?|st)\.?$", re.U + re.I)
__abbrev = re.compile(r"\b(i\.e\.|e\.g\.|c-à-d)", re.U + re.I)
__digit_valid = set("0123456789,.-")
__simple_smileys = re.compile("^[:;x=],?-?[()DdPp]+$")

__forbidden = [__is_abn, __abbrev, __simple_smileys]

__force = [url_re, email_re, __cls, re.compile("'{2,}")]

__word = re.compile("^[^\\W\\d]+$", re.U + re.M)
__number_with_unit = re.compile("([0-9][^0-9,.])|([^0-9,.][0-9])")
__atomic = re.compile('[;:«»()\\[\\]{}=+*$£€/\\"?!…%€$£]')
__comma_not_number = re.compile("(?<=[^0-9]),(?![0-9])", re.U + re.M)
__apostrophe = re.compile("(?=['ʼ’])", re.U + re.M)


def bounds2spans(bounds):
    """Create spans from bounds."""
    spans = [Span(bounds[i].end, bounds[i + 1].start) for i in range(0, len(bounds) - 1)]
    spans = [span for span in spans if span.start != span.end]
    return spans


def sentence_spans(content, token_spans):
    return bounds2spans(sentence_bounds(content, token_spans))


def paragraph_bounds(content, sentence_spans, token_spans):
    """Return a list of bounds matching paragraphs.

    Parameters
    ----------
    content : str
        the content to find paragraph bounds for.
    sentence_spans : list[Span]
        the list of sentence spans.
    token_spans : list[Span]
        the list of token spans.

    Returns
    -------
    list[Span]
        The list of paragraph bounds in content.
    """

    s_spans = [Span(token_spans[e.start].start, token_spans[e.end - 1].end) for e in sentence_spans]
    bounds = [Span(0, 0)]
    for index, sentence in enumerate(sentence_spans[1:], 1):
        substring = content[s_spans[index - 1].end: s_spans[index].start]
        if substring.count("\n") > 1:
            bounds.append(Span(index, index))
    bounds.append(Span(len(sentence_spans), len(sentence_spans)))

    return bounds


def paragraph_spans(content, sentence_spans, token_spans):
    return bounds2spans(paragraph_bounds(content, sentence_spans, token_spans))


def word_spans(content):
    spans = []
    offset = 0

    part = content
    l1 = [match.span() for match in __spaces.finditer(part)]

    if l1:
        l2 = [(l1[i][1], l1[i + 1][0]) for i in range(len(l1) - 1)]
        if l1[0][0] != 0:
            l2.insert(0, (0, l1[0][0]))
        if l1[-1][1] != len(part):
            l2.append((l1[-1][1], len(part)))
    else:
        l2 = [(0, len(part))]

    i = 0
    while i < len(l2):
        span = l2[i]
        text = part[span[0]: span[1]]
        shift = span[0]
        if len(text) == 1:
            i += 1
            continue
        if __word.match(text):
            i += 1
            continue
        found = False
        for force in __force:
            found = force.search(text)
            if found:
                s, e = found.start(), found.end()
                del l2[i]
                l2.insert(i, (shift + e, shift + len(text)))
                l2.insert(i, (shift + s, shift + e))
                l2.insert(i, (shift, shift + s))
                i += 2
                break
        if found:
            continue
        for forbidden in __forbidden:
            found = forbidden.match(text)
            if found:
                i += 1
                break
        if found:
            continue
        tmp = []
        # atomic characters, they are always split
        prev = span[0]
        for find in __atomic.finditer(text):
            if prev != shift + find.start():
                tmp.append((prev, shift + find.start()))
            tmp.append((shift + find.start(), shift + find.end()))
            prev = shift + find.end()
        if tmp:
            if prev != span[1]:
                tmp.append((prev, span[1]))
            del l2[i]
            for t in reversed(tmp):
                l2.insert(i, t)
            continue
        # commas
        prev = span[0]
        find = __comma_not_number.search(text)
        if find:
            tmp.extend(
                [
                    (prev, shift + find.start()),
                    (shift + find.start(), shift + find.end()),
                    (shift + find.end(), span[1]),
                ]
            )
            prev = shift + find.end() + 1
        if tmp:
            del l2[i]
            for t in reversed(tmp):
                l2.insert(i, t)
            continue
        # apostrophes
        prev = span[0]
        for find in __apostrophe.finditer(text):
            tmp.append((prev, shift + find.start() + 1))
            prev = shift + find.start() + 1
        if prev < span[1]:
            tmp.append((prev, span[1]))
        if len(tmp) > 1:
            del l2[i]
            for t in reversed(tmp):
                l2.insert(i, t)
            continue
        del tmp[:]
        # number with unit
        prev = span[0]
        for find in __number_with_unit.finditer(text):
            tmp.append((prev, span[0] + find.start() + 1))
            prev = span[0] + find.start() + 1
        if tmp:
            tmp.append((prev, span[1]))
            del l2[i]
            for t in reversed(tmp):
                l2.insert(i, t)
            continue
        # dots and ending commas
        # ~ if text and (text[-1] in ".," and not (len(text) == 2 and text[0].isupper())):
            # ~ mdots = __dots.search(text)
            # ~ length = len(mdots.group(1)) if mdots else 1
            # ~ if length != len(text):
                # ~ tmp = [(span[0], span[1] - length), (span[1] - length, span[1])]
        if text and text[-1] in ".,":
            if not (len(text) == 2 and text[0].isupper()):
                mdots = __dots.search(text)
                length = len(mdots.group(1)) if mdots else 1
                if length != len(text):
                    tmp = [(span[0], span[1] - length), (span[1] - length, span[1])]
                    # print(tmp, text)
            else:
                if content[l2[i-1][0]: l2[i-1][1]].lower() in {"groupe", "classe"}:
                    tmp = [(l2[i][0], l2[i][0]+1), (l2[i][0]+1, l2[i][1])]
        if tmp:
            del l2[i]
            for t in reversed(tmp):
                l2.insert(i, t)
            continue
        i += 1

    spans = [Span(s[0] + offset, s[1] + offset) for s in l2 if s[0] < s[1]]
    spans = [span for span in spans if len(span) > 0]
    return spans


def sentence_bounds(content, token_spans):
    sent_bounds = []
    tokens = [content[t.start: t.end] for t in token_spans]
    opening_counts = [0 for i in token_spans]
    count = 0
    for i in range(len(opening_counts)):
        if tokens[i] in "«([":
            count += 1
        elif tokens[i] in "»)]":
            count -= 1
        opening_counts[i] = count

    sent_bounds.append(Span(0, 0))
    for index, span in enumerate(token_spans):
        token = tokens[index]
        if re.match("^[?!]+$", token) or token == "…" or re.match("\\.\\.+", token):
            sent_bounds.append(Span(index + 1, index + 1))
        elif token == ".":
            if opening_counts[index] == 0:
                sent_bounds.append(Span(index + 1, index + 1))
        elif (
            index < len(token_spans) - 1
            and content[span.end: token_spans[index + 1].start].count("\n") > 1
        ):
            sent_bounds.append(Span(index + 1, index + 1))
    sent_bounds.append(Span(len(tokens), len(tokens)))

    return sent_bounds
