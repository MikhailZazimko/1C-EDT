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
    def test_admin_journal_access_uses_platform_right_and_allows_missing_worker(self):
        code = (ROOT / 'CommonModules/Расш1_ВыработкаСервер/Module.bsl').read_text(encoding='utf-8-sig')
        context = re.search(r'Функция КонтекстРаботника\(\).*?КонецФункции', code, re.S).group()
        # Право проверяется в текущем сеансе; имя учётной записи не даёт привилегий.
        self.assertIn('ЭтоАдминистратор = ПравоДоступа("Администрирование", Метаданные)', context)
        self.assertNotRegex(context, r'ИмяВхода\s*=\s*"Администратор"')
        self.assertIn('Если НЕ ЕстьСопоставление И НЕ ЭтоАдминистратор Тогда', context)
        self.assertIn('Если НЕ ЗначениеЗаполнено(Работник) И НЕ ЭтоАдминистратор Тогда', context)
        self.assertLess(context.index('Если ЭтоАдминистратор Тогда'), context.index('ИначеЕсли РольДоступна("Мастер")'))
        self.assertIn('Если ЭтоАдминистратор ИЛИ Роль = "Мастер" Тогда', context)

    def test_admin_read_access_does_not_remove_worker_validation_on_write(self):
        code = (ROOT / 'CommonModules/Расш1_ВыработкаСервер/Module.bsl').read_text(encoding='utf-8-sig')
        check = re.search(r'Процедура ПроверитьДокумент\(Документ\).*?КонецПроцедуры', code, re.S).group()
        self.assertIn('ПроверитьДоступКЗаказу(Документ.Заказ, Документ.Участок, Истина)', check)
        self.assertIn('Документ.Работник <> Контекст.Работник', check)
        access = re.search(r'Функция ПроверитьДоступКЗаказу\(.*?КонецФункции', code, re.S).group()
        self.assertRegex(access, r'Если ТребуетсяРаботник И НЕ ЗначениеЗаполнено\(Контекст\.Работник\) Тогда\s+ВызватьИсключение')
        form = DOCUMENT.with_name('Module.bsl').read_text(encoding='utf-8-sig')
        new_portion = re.search(r'Функция НоваяПорция\(.*?КонецФункции', form, re.S).group()
        self.assertIn('ПроверитьДоступКЗаказу(Заказ, Участок, Истина)', new_portion)

    def test_object_module_only_compiles_where_server_dependency_exists(self):
        code = (ROOT / 'Documents/Выработка/ObjectModule.bsl').read_text(encoding='utf-8-sig').strip()
        guard = re.match(r'#Если\s+(.+)\s+Тогда\s*\n', code)
        self.assertIsNotNone(guard, 'Server-only calls must not compile in the thick managed client')
        contexts = set(re.split(r'\s+Или\s+', guard.group(1)))
        module = ET.parse(ROOT / 'CommonModules/Расш1_ВыработкаСервер/Расш1_ВыработкаСервер.mdo').getroot()
        context_flags = {'Сервер': 'server', 'ВнешнееСоединение': 'externalConnection',
                         'ТолстыйКлиентОбычноеПриложение': 'clientOrdinaryApplication'}
        self.assertEqual(contexts, set(context_flags))
        for context in contexts:
            self.assertEqual(module.findtext(context_flags[context]), 'true')
        self.assertTrue(code.endswith('#КонецЕсли'))
        self.assertEqual(len(re.findall(r'^#Если\b', code, re.M)), 1)
        self.assertEqual(len(re.findall(r'^#КонецЕсли\b', code, re.M)), 1)

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
