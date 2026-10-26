"""Структурные проверки проекта EDT без установленной платформы 1С.

Они проверяют экспортированные формы/метаданные, а не исполняют BSL.
Сценарии в информационной базе перечислены в docs/acceptance.md.
"""

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1] / 'АРМ_для_КМК' / 'src'
JOURNAL = ROOT / 'CommonForms/ЖурналЗаказовВРаботу/Form.form'
DOCUMENT = ROOT / 'Documents/Выработка/Forms/ФормаДокумента/Form.form'
XSI = '{http://www.w3.org/2001/XMLSchema-instance}'
RIGHTS = {'r': 'http://v8.1c.ru/8.2/roles'}


def control(form, name):
    return next(c for c in form.iter('items') if c.findtext('name') == name)


def document_column(name):
    doc = ET.parse(ROOT / 'Documents/Выработка/Выработка.mdo').getroot()
    products = next(c for c in doc.findall('tabularSections') if c.findtext('name') == 'Продукция')
    return next(c for c in products.findall('attributes') if c.findtext('name') == name)


class EDTContractTest(unittest.TestCase):
    def test_all_exported_xml_is_well_formed(self):
        for p in ROOT.rglob('*'):
            if p.suffix in {'.mdo', '.form', '.rights', '.cmi'}:
                with self.subTest(path=str(p.relative_to(ROOT))):
                    ET.parse(p)

    def test_new_configuration_members_resolve(self):
        config = ET.parse(ROOT / 'Configuration/Configuration.mdo').getroot()
        for tag, folder in [('commonModules', 'CommonModules'), ('commonCommands', 'CommonCommands'), ('informationRegisters', 'InformationRegisters')]:
            for c in config.findall(tag):
                name = c.text.split('.', 1)[1]
                with self.subTest(name=name):
                    self.assertTrue((ROOT / folder / name / (name + '.mdo')).is_file())

    def test_metadata_root_uuids_are_unique(self):
        uuids = {}
        for p in ROOT.rglob('*.mdo'):
            uid = ET.parse(p).getroot().get('uuid')
            if uid:
                self.assertNotIn(uid, uuids, f'{p} duplicates {uuids.get(uid)}')
                uuids[uid] = p

    def test_form_control_names_and_ids_are_unique(self):
        for p in [JOURNAL, DOCUMENT]:
            form = ET.parse(p).getroot()
            for tag in ['name', 'id']:
                values = [c.findtext(tag) for c in form.iter('items')]
                self.assertEqual(len(values), len(set(values)), str(p))

    def test_form_handlers_exist_in_the_correct_context(self):
        expected_counts = {'OnCreateAtServer': 2, 'NotificationProcessing': 3, 'Selection': 4,
                           'OnChange': 1, 'BeforeClose': 4, 'BeforeWrite': 2}
        for p in [JOURNAL, DOCUMENT]:
            code = p.with_name('Module.bsl').read_text(encoding='utf-8-sig')
            form = ET.parse(p).getroot()
            for handler in form.iter('handlers'):
                event, name = handler.findtext('event'), handler.findtext('name')
                with self.subTest(form=str(p), handler=name):
                    context = 'НаСервере' if event == 'OnCreateAtServer' else 'НаКлиенте'
                    match = re.search(r'&' + context + r'\s+Процедура\s+' + name + r'\(([^)]*)\)', code)
                    self.assertIsNotNone(match)
                    self.assertEqual(len(match.group(1).split(',')), expected_counts[event])
            for cmd in form.findall('formCommands'):
                name = cmd.findtext('action/handler/name')
                self.assertRegex(code, r'&НаКлиенте\s+Процедура\s+' + name + r'\(Команда\)')

    def test_journal_has_exactly_seven_distinct_columns(self):
        form = ET.parse(JOURNAL).getroot()
        table = control(form, 'СписокЗаказов')
        paths = [c.findtext('dataPath/segments') for c in table.findall('items')]
        expected = ['Заказ', 'Участок', 'Изделие', 'План', 'Выполнено', 'Осталось', 'Статус']
        expected[0] = 'НомерЗаказа'
        self.assertEqual(paths, ['СписокЗаказов.' + name for name in expected])
        self.assertEqual(table.findtext('readOnly'), 'true')
        self.assertEqual(table.findtext('changeRowSet'), 'false')
        self.assertEqual(table.findtext('handlers/event'), 'Selection')

    def test_only_two_production_columns_are_editable(self):
        form = ET.parse(DOCUMENT).getroot()
        table = control(form, 'Продукция')
        fields = table.findall('items')
        self.assertEqual(len(fields), 7)
        paths = [c.findtext('dataPath/segments') for c in fields]
        self.assertEqual(len(paths), len(set(paths)))
        editable = {c.findtext('dataPath/segments') for c in fields if c.findtext('readOnly') != 'true'}
        self.assertEqual(editable, {'Объект.Продукция.Выполнено', 'Объект.Продукция.Брак'})
        for c in fields:
            if c.findtext('dataPath/segments') in editable:
                self.assertEqual(c.findtext('handlers/name'), 'КоличествоПриИзменении')
        self.assertEqual(table.findtext('changeRowSet'), 'false')

    def test_header_is_readonly_and_has_two_columns(self):
        form = ET.parse(DOCUMENT).getroot()
        header = control(form, 'Шапка')
        self.assertEqual(header.findtext('extInfo/group'), 'Horizontal')
        self.assertEqual(len(header.findall('items')), 2)
        for name in ['Заказ', 'Участок', 'Работник', 'Дата']:
            self.assertEqual(control(form, name).findtext('readOnly'), 'true')

    def test_quantities_are_nonnegative_integers_and_remaining_is_signed(self):
        for name in ['Выполнено', 'Брак']:
            qualifiers = document_column(name).find('type/numberQualifiers')
            self.assertEqual(qualifiers.findtext('scale'), '0')
            self.assertEqual(qualifiers.findtext('nonNegative'), 'true')
        self.assertEqual(document_column('Осталось').findtext('type/numberQualifiers/nonNegative'), 'false')

    def test_order_line_identity_exists_in_document_and_register(self):
        name = 'Расш1_НомерСтрокиЗаказа'
        self.assertEqual(document_column(name).findtext('type/types'), 'Number')
        reg = ET.parse(ROOT / 'AccumulationRegisters/ВыработкаПоЗаказам/ВыработкаПоЗаказам.mdo').getroot()
        self.assertIn(name, [c.findtext('name') for c in reg.findall('dimensions')])

    def test_no_automatic_standard_document_save_commands(self):
        form = ET.parse(DOCUMENT).getroot()
        self.assertEqual(form.findtext('autoCommandBar/autoFill'), 'false')
        self.assertEqual({c.findtext('name') for c in form.findall('formCommands')},
                         {'ЗаписатьПорцию', 'ЗаписатьИЗакрытьПорцию', 'ЗакрытьБезЗаписи'})
        self.assertEqual(control(form, 'ЗаписатьИЗакрытьПорцию').findtext('defaultButton'), 'true')
        self.assertIn('BeforeWrite', [h.findtext('event') for h in form.findall('handlers')])

    def test_all_roles_can_record_production_but_only_master_edits_mapping(self):
        for name in ['Оператор', 'Мастер', 'Контролер']:
            form = ET.parse(ROOT / f'Roles/{name}/Rights.rights').getroot()
            rights = {}
            for obj in form.findall('r:object', RIGHTS):
                rights[obj.findtext('r:name', namespaces=RIGHTS)] = {
                    r.findtext('r:name', namespaces=RIGHTS)
                    for r in obj.findall('r:right', RIGHTS)
                    if r.findtext('r:value', namespaces=RIGHTS) == 'true'}
            self.assertTrue({'Read', 'Insert', 'Update', 'Posting'} <= rights['Document.Выработка'])
            mapping = rights['InformationRegister.Расш1_РаботникиПользователей']
            self.assertEqual('Update' in mapping, name == 'Мастер')
            self.assertIn('View', rights['CommonCommand.Расш1_ЖурналЗаказовВРаботу'])


if __name__ == '__main__':
    unittest.main()
