"""Готовит точечные исправления двух предоставленных XDTO-пакетов УНФ.

Основной проект не включён в репозиторий расширения. Результат сохраняется
отдельно в fixes/xdto и переносится в основной проект после проверки.
XML правится побайтно: пространства имён и остальная сериализация сохраняются.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import zipfile
from pathlib import Path
from xml.dom import minidom

XDTO = 'http://v8.1c.ru/8.1/xdto'
XS = 'http://www.w3.org/2001/XMLSchema'
FSS = 'http://pilot.fss.ru/1.7'
MOBILE = 'http://www.1c.ru/SB/MobileExchange'
ROOT = Path(__file__).resolve().parents[1]


def children(node, name):
    return [c for c in node.childNodes if c.nodeType == c.ELEMENT_NODE
            and c.namespaceURI == XDTO and c.localName == name]


def resolve(node, value):
    prefix, local = value.split(':', 1) if ':' in value else ('', value)
    attribute = 'xmlns:' + prefix if prefix else 'xmlns'
    current = node
    while current.nodeType == current.ELEMENT_NODE:
        if current.hasAttribute(attribute):
            return current.getAttribute(attribute), local
        current = current.parentNode
    raise ValueError('Не разрешено имя типа: ' + value)


def parse(data, namespace):
    root = minidom.parseString(data).documentElement
    if root.namespaceURI != XDTO or root.localName != 'package' or root.getAttribute('targetNamespace') != namespace:
        raise ValueError('Файл относится к другому XDTO-пакету')
    if resolve(root, 'xs:integer') != (XS, 'integer'):
        raise ValueError('Неожиданное пространство имён xs')
    return root


def text(node):
    return ''.join(c.data for c in node.childNodes if c.nodeType in (c.TEXT_NODE, c.CDATA_SECTION_NODE))


def property_path(node):
    names = []
    while node.nodeType == node.ELEMENT_NODE:
        if node.localName == 'property':
            names.append(node.getAttribute('name'))
        node = node.parentNode
    return '/'.join(reversed(names))


def repair_fss(data):
    root = parse(data, FSS)
    types = {n.getAttribute('name'): n for n in children(root, 'valueType')}
    empty = types['fssempty']
    if (resolve(empty, empty.getAttribute('base')) != (XS, 'string')
            or len(children(empty, 'enumeration')) != 1 or text(children(empty, 'enumeration')[0]) != ''):
        raise ValueError('Изменилось определение пустой строки fssempty')
    for name, digits in [('fssnilinteger1', '1'), ('fssnilinteger2', '2')]:
        node = types[name]
        members = children(node, 'typeDef')
        if (node.getAttribute('variety') != 'Union' or len(members) != 2
                or resolve(members[0], members[0].getAttribute('base')) != (XS, 'integer')
                or members[0].getAttribute('totalDigits') != digits
                or resolve(members[1], members[1].getAttribute('base')) != (FSS, 'fssempty')):
            raise ValueError('Изменился состав числового объединения ' + name)

    targets = []
    for node in root.getElementsByTagNameNS(XDTO, 'typeDef'):
        enums = children(node, 'enumeration')
        if not enums or not node.hasAttribute('base'):
            continue
        base = resolve(node, node.getAttribute('base'))
        if base not in [(FSS, 'fssnilinteger1'), (FSS, 'fssnilinteger2')]:
            continue
        values = [text(e) for e in enums]
        digits = int(types[base[1]].getElementsByTagNameNS(XDTO, 'typeDef')[0].getAttribute('totalDigits'))
        if (node.getAttribute('variety') != 'Atomic'
                or any(not re.fullmatch(r'[+-]?[0-9]+', value) or len(str(abs(int(value)))) > digits for value in values)
                or any(c.localName != 'enumeration' for c in node.childNodes if c.nodeType == c.ELEMENT_NODE)):
            raise ValueError('Ограничение требует отдельного анализа: ' + property_path(node))
        targets.append((node, values, digits))
    if len(targets) != 27:
        raise ValueError(f'Ожидалось 27 числовых перечислений, найдено {len(targets)}')

    # Во всех 27 списках есть только непустые целые коды, укладывающиеся
    # в totalDigits базового объединения. Пустая строка исключена enumeration.
    # Следовательно, integer + тот же enumeration задаёт тот же набор значений.
    pattern = re.compile(rb'(?P<tag><typeDef\b[^>]*\bbase="(?P<base>[^"]+:fssnilinteger[12])"[^>]*>)(?=\s*<enumeration(?:\s|/|>))')
    matches = list(pattern.finditer(data))
    if len(matches) != len(targets):
        raise ValueError('Сериализация файла изменилась: список замен не совпал с моделью')
    changes = []
    for match, (node, values, digits) in zip(matches, targets):
        old_base = match.group('base').decode('utf-8')
        if old_base != node.getAttribute('base'):
            raise ValueError('Порядок XML-описаний изменился')
        old = b'base="' + match.group('base') + b'"'
        new = b'base="xs:integer"'
        start = match.start('tag') + match.group('tag').index(old)
        changes.append({'offset': start, 'old': old.decode(), 'new': new.decode(),
                        'property': property_path(node), 'base': old_base,
                        'codes': values, 'inherited_total_digits': digits,
                        'line': data.count(b'\n', 0, start) + 1})
    result = data
    for change in reversed(changes):
        start = change['offset']
        old, new = change['old'].encode(), change['new'].encode()
        if result[start:start + len(old)] != old:
            raise ValueError('Не совпал исходный текст замены')
        result = result[:start] + new + result[start + len(old):]
    return result, changes


def repair_mobile(data):
    root = parse(data, MOBILE)
    objects = {n.getAttribute('name'): n for n in children(root, 'objectType')}
    company = objects['Company']
    if resolve(company, company.getAttribute('base')) != (MOBILE, 'Object'):
        raise ValueError('Изменился базовый тип Company')
    parent_name = next(p for p in children(objects['Object'], 'property') if p.getAttribute('name') == 'name')
    name = next(p for p in children(company, 'property') if p.getAttribute('name') == 'name')
    inherited_min = int(parent_name.getAttribute('lowerBound') or '1')
    effective_min = int(name.getAttribute('lowerBound') or '1')
    if inherited_min != 0 or effective_min != 1 or resolve(name, name.getAttribute('type')) != (XS, 'string'):
        raise ValueError('Границы Company.name требуют отдельного анализа')
    if name.hasAttribute('lowerBound'):
        raise ValueError('У Company.name нижняя граница уже указана явно')
    # В присланном XML нет сужения ниже базовой границы: 1 >= 0.
    # Делаем значение по умолчанию явным; границу до 0 не понижаем.
    pattern = re.compile(rb'<objectType\b(?=[^>]*\bname="Company")[^>]*>\s*(?P<property><property\b(?=[^>]*\bname="name")[^>]*/>)')
    matches = list(pattern.finditer(data))
    if len(matches) != 1:
        raise ValueError('Не найдено единственное объявление Company.name')
    match = matches[0]
    old = match.group('property')
    new = old[:-2] + b' lowerBound="1"/>'
    offset = match.start('property')
    return data[:offset] + new + data[offset + len(old):], [
        {'offset': offset, 'old': old.decode(), 'new': new.decode(), 'property': 'Company.name',
         'line': data.count(b'\n', 0, offset) + 1,
         'inherited_lower_bound': inherited_min, 'effective_lower_bound': effective_min}]


def prepare(mobile_path, fss_path, output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'note': 'Копии для проверки в основной УНФ; EDT/платформа в облаке отсутствуют.', 'packages': []}
    patch = []
    for name, path, repair in [('MobileClientIntegration', mobile_path, repair_mobile),
                               ('ОтправкаРеестровПВСО', fss_path, repair_fss)]:
        original = path.read_bytes()
        fixed, changes = repair(original)
        target = output / name / 'Package.xdto'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(fixed)
        manifest['packages'].append({'name': name, 'original_sha256': hashlib.sha256(original).hexdigest(),
                                     'fixed_sha256': hashlib.sha256(fixed).hexdigest(), 'changes': changes})
        relative = f'УНФ_Демо_КМК/src/XDTOPackages/{name}/Package.xdto'
        patch.extend(difflib.unified_diff(original.decode('utf-8').splitlines(keepends=True),
                                         fixed.decode('utf-8').splitlines(keepends=True),
                                         fromfile=relative, tofile=relative))
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'unf-xdto.patch').write_bytes(''.join(patch).encode('utf-8'))
    with zipfile.ZipFile(output / 'unf-xdto-fixed.zip', 'w') as archive:
        for package in manifest['packages']:
            relative = f"src/XDTOPackages/{package['name']}/Package.xdto"
            entry = zipfile.ZipInfo(relative, date_time=(2026, 10, 27, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (output / package['name'] / 'Package.xdto').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mobile', type=Path, required=True)
    parser.add_argument('--fss', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'fixes/xdto')
    args = parser.parse_args()
    prepare(args.mobile, args.fss, args.output)
