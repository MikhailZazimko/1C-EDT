"""Проверяет точность исправления XDTO и совместимость числовых ограничений.

XSD-проверки используют lxml при его наличии. Они проверяют пространство
допустимых значений схемы, а не поведение фабрики XDTO платформы 1С.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zipfile

try:
    from lxml import etree as XML
except ImportError:
    XML = None

ROOT = Path(__file__).resolve().parents[1]
FIXES = ROOT / 'fixes/xdto'
XD = 'http://v8.1c.ru/8.1/xdto'
XS = 'http://www.w3.org/2001/XMLSchema'
FSS = 'http://pilot.fss.ru/1.7'
NS = {'d': XD}
spec = importlib.util.spec_from_file_location('repair_unf_xdto', ROOT / 'tools/repair_unf_xdto.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def original_bytes(fixed, package):
    positions = []
    delta = 0
    for change in package['changes']:
        positions.append((change['offset'] + delta, change))
        delta += len(change['new'].encode('utf-8')) - len(change['old'].encode('utf-8'))
    data = fixed
    for offset, change in reversed(positions):
        new, old = change['new'].encode('utf-8'), change['old'].encode('utf-8')
        if data[offset:offset + len(new)] != new:
            raise AssertionError('Не совпала точечная замена')
        data = data[:offset] + old + data[offset + len(new):]
    return data


def xsd_name(node, name):
    if name.startswith('{'):
        uri, local = name[1:].split('}', 1)
    elif ':' in name:
        prefix, local = name.split(':', 1)
        uri = node.nsmap[prefix]
    else:
        uri, local = node.nsmap[None], name
    if uri == XS:
        return 'xs:' + local
    if uri == FSS:
        return 'tns:' + local
    raise AssertionError('Неожиданное пространство типа: ' + uri)


def simple_type(parent, source, name=None):
    target = XML.SubElement(parent, '{' + XS + '}simpleType')
    if name:
        target.set('name', name)
    if source.get('variety') == 'Union':
        body = XML.SubElement(target, '{' + XS + '}union')
        if source.get('memberTypes'):
            body.set('memberTypes', ' '.join(xsd_name(source, n) for n in source.get('memberTypes').split()))
        for child in source.findall('d:typeDef', NS):
            simple_type(body, child)
    else:
        body = XML.SubElement(target, '{' + XS + '}restriction', base=xsd_name(source, source.get('base')))
        for name in ['totalDigits', 'fractionDigits', 'maxLength', 'minLength', 'length']:
            if source.get(name) is not None:
                XML.SubElement(body, '{' + XS + '}' + name, value=source.get(name))
        for child in source:
            if XML.QName(child).localname in ['enumeration', 'pattern']:
                XML.SubElement(body, '{' + XS + '}' + XML.QName(child).localname, value=child.text or '')
    return target


def value_schema(root, source):
    schema = XML.Element('{' + XS + '}schema', nsmap={'xs': XS, 'tns': FSS}, targetNamespace=FSS)
    for node in root.findall('d:valueType', NS):
        simple_type(schema, node, node.get('name'))
    element = XML.SubElement(schema, '{' + XS + '}element', name='value')
    simple_type(element, source)
    return XML.XMLSchema(schema)


class XdtoFixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packages = json.loads((FIXES / 'manifest.json').read_text(encoding='utf-8'))['packages']

    def test_only_the_documented_attributes_changed_in_uploaded_files(self):
        for package in self.packages:
            fixed = (FIXES / package['name'] / 'Package.xdto').read_bytes()
            self.assertEqual(hashlib.sha256(fixed).hexdigest(), package['fixed_sha256'])
            original = original_bytes(fixed, package)
            self.assertEqual(hashlib.sha256(original).hexdigest(), package['original_sha256'])
            function = repair.repair_mobile if package['name'] == 'MobileClientIntegration' else repair.repair_fss
            regenerated, changes = function(original)
            self.assertEqual(regenerated, fixed)
            self.assertEqual(changes, package['changes'])

    def test_zip_contains_only_the_two_fixed_packages_at_project_paths(self):
        with zipfile.ZipFile(FIXES / 'unf-xdto-fixed.zip') as archive:
            expected = {f"src/XDTOPackages/{p['name']}/Package.xdto" for p in self.packages}
            self.assertEqual(set(archive.namelist()), expected)
            for package in self.packages:
                data = archive.read(f"src/XDTOPackages/{package['name']}/Package.xdto")
                self.assertEqual(hashlib.sha256(data).hexdigest(), package['fixed_sha256'])

    def test_company_name_keeps_its_required_default_cardinality(self):
        package = next(p for p in self.packages if p['name'] == 'MobileClientIntegration')
        fixed = (FIXES / package['name'] / 'Package.xdto').read_bytes()
        before = ET.fromstring(original_bytes(fixed, package))
        after = ET.fromstring(fixed)
        parent = after.find("d:objectType[@name='Object']/d:property[@name='name']", NS)
        original = before.find("d:objectType[@name='Company']/d:property[@name='name']", NS)
        updated = after.find("d:objectType[@name='Company']/d:property[@name='name']", NS)
        self.assertEqual(original.get('lowerBound', '1'), updated.get('lowerBound'))
        self.assertGreaterEqual(int(updated.get('lowerBound')), int(parent.get('lowerBound', '1')))
        self.assertEqual(len(package['changes']), 1)

    def test_only_27_numeric_anonymous_restrictions_are_rebased(self):
        package = next(p for p in self.packages if p['name'] == 'ОтправкаРеестровПВСО')
        self.assertEqual(len(package['changes']), 27)
        for change in package['changes']:
            self.assertEqual(change['new'], 'base="xs:integer"')
            self.assertNotIn('', change['codes'])

    @unittest.skipIf(XML is None, 'XSD validation requires lxml')
    def test_numeric_restrictions_accept_the_same_xml_values(self):
        package = next(p for p in self.packages if p['name'] == 'ОтправкаРеестровПВСО')
        fixed = (FIXES / package['name'] / 'Package.xdto').read_bytes()
        before, after = XML.fromstring(original_bytes(fixed, package)), XML.fromstring(fixed)
        old_types = before.xpath('.//d:typeDef[d:enumeration]', namespaces=NS)
        new_types = after.xpath('.//d:typeDef[d:enumeration]', namespaces=NS)
        self.assertEqual(len(old_types), len(new_types))
        checked = 0
        for old, new in zip(old_types, new_types):
            if old.get('base') == new.get('base'):
                continue
            old_schema, new_schema = value_schema(before, old), value_schema(after, new)
            expected = {int(n.text) for n in old.findall('d:enumeration', NS)}
            for number in range(-100, 101):
                for lexical in [str(number), f'{number:+d}', f'{number:04d}', ' \t' + str(number) + '\n']:
                    value = XML.Element('{' + FSS + '}value')
                    value.text = lexical
                    self.assertEqual(old_schema.validate(value), number in expected, (old.getparent().get('name'), lexical))
                    self.assertEqual(new_schema.validate(value), old_schema.validate(value), lexical)
            for lexical in ['', ' ', '1.0', '1e0', 'abc', 'true', '999999999999999999999999999']:
                value = XML.Element('{' + FSS + '}value')
                value.text = lexical
                self.assertFalse(old_schema.validate(value), lexical)
                self.assertFalse(new_schema.validate(value), lexical)
            checked += 1
        self.assertEqual(checked, 27)

    @unittest.skipIf(XML is None, 'XSD validation requires lxml')
    def test_string_codes_with_leading_zeroes_and_empty_values_stay_unchanged(self):
        package = next(p for p in self.packages if p['name'] == 'ОтправкаРеестровПВСО')
        fixed = (FIXES / package['name'] / 'Package.xdto').read_bytes()
        before, after = XML.fromstring(original_bytes(fixed, package)), XML.fromstring(fixed)
        for name in ['IdType', 'CalcConditionType', 'RelationCodeType', 'fssnilinteger1', 'fssnilinteger2', 'fssnildate']:
            old = before.find(f"d:valueType[@name='{name}']", NS)
            new = after.find(f"d:valueType[@name='{name}']", NS)
            self.assertEqual(XML.tostring(old), XML.tostring(new))
        ids = after.find("d:valueType[@name='IdType']", NS)
        schema = value_schema(after, ids)
        for lexical, expected in [('01', True), ('1', False), ('', False), ('99', False)]:
            value = XML.Element('{' + FSS + '}value')
            value.text = lexical
            self.assertEqual(schema.validate(value), expected, lexical)
        empty_integer = after.find("d:valueType[@name='fssnilinteger1']", NS)
        schema = value_schema(after, empty_integer)
        for lexical, expected in [('', True), ('1', True), ('10', False)]:
            value = XML.Element('{' + FSS + '}value')
            value.text = lexical
            self.assertEqual(schema.validate(value), expected, lexical)


if __name__ == '__main__':
    unittest.main()
