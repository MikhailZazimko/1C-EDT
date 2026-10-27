"""Проверки связности новых метаданных EDT; расчёты исполняются в OneScript.

Эти проверки не заменяют компиляцию EDT с исходниками базовой УНФ.
"""
from pathlib import Path
import json
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / 'АРМ_для_КМК/src'
NAME = 'Расш1_ТехническиеЛисты'
DIR = ROOT / 'Catalogs' / NAME
FORM = DIR / 'Forms/ФормаЭлемента/Form.form'
NS = {'r': 'http://v8.1c.ru/8.2/roles'}


def all_rights(role):
    root = ET.parse(ROOT / f'Roles/{role}/Rights.rights').getroot()
    return {o.findtext('r:name', namespaces=NS): {
        right.findtext('r:name', namespaces=NS) for right in o.findall('r:right', NS)
        if right.findtext('r:value', namespaces=NS) == 'true'} for o in root.findall('r:object', NS)}


class TechSheetMetadataTest(unittest.TestCase):
    def test_metadata_reference_types_resolve_in_the_extension(self):
        # Проверяем и контролируемые типы заимствованных реквизитов:
        # платформа должна разрешить их ещё при загрузке расширения.
        folders = {'CatalogRef': 'Catalogs', 'EnumRef': 'Enums'}
        unresolved = []
        for path in ROOT.rglob('*.mdo'):
            for node in ET.parse(path).getroot().iter():
                value = (node.text or '').strip()
                prefix, separator, name = value.partition('.')
                if separator and prefix in folders:
                    target = ROOT / folders[prefix] / name / (name + '.mdo')
                    if not target.is_file():
                        unresolved.append(f'{path.relative_to(ROOT)}: {value}')
        self.assertEqual(unresolved, [], '\n'.join(unresolved))

    def test_new_objects_are_registered_and_have_valid_references(self):
        config = ET.parse(ROOT / 'Configuration/Configuration.mdo').getroot()
        folders = {'catalogs': 'Catalogs', 'enums': 'Enums', 'roles': 'Roles',
                   'commonModules': 'CommonModules', 'informationRegisters': 'InformationRegisters',
                   'eventSubscriptions': 'EventSubscriptions'}
        for tag, folder in folders.items():
            for ref in config.findall(tag):
                name = ref.text.split('.', 1)[1]
                self.assertTrue((ROOT / folder / name / (name + '.mdo')).is_file(), ref.text)
                if folder == 'CommonModules':
                    self.assertTrue((ROOT / folder / name / 'Module.bsl').is_file(), ref.text)
        for path in ROOT.glob('Catalogs/Расш1_*/*.mdo'):
            for node in ET.parse(path).getroot().iter('types'):
                value = node.text or ''
                if value.startswith('CatalogRef.'):
                    name = value.split('.', 1)[1]
                    self.assertTrue((ROOT / 'Catalogs' / name / (name + '.mdo')).is_file(), value)
                elif value.startswith('EnumRef.'):
                    name = value.split('.', 1)[1]
                    self.assertTrue((ROOT / 'Enums' / name / (name + '.mdo')).is_file(), value)

    def test_fields_from_the_pdf_have_numeric_types_and_repeatable_sections(self):
        meta = ET.parse(DIR / (NAME + '.mdo')).getroot()
        attributes = {a.findtext('name'): a for a in meta.findall('attributes')}
        for name in ['ШиринаМм', 'ВысотаМм', 'ТолщинаМм', 'ПрипускРезкиМм', 'СопротивлениеОтОм',
                     'СопротивлениеДоОм', 'ДопускПрилеганияМм', 'ТолщинаНитиМм']:
            self.assertEqual(attributes[name].findtext('type/types'), 'Number')
        self.assertEqual(attributes['Индивидуальный'].findtext('type/types'), 'Boolean')
        self.assertEqual(attributes['ПредыдущаяРедакция'].findtext('type/types'), 'CatalogRef.' + NAME)
        tables = {t.findtext('name'): t for t in meta.findall('tabularSections')}
        self.assertTrue({'Операции', 'Отверстия', 'СлоиПечати', 'Коннекторы', 'Материалы',
                         'РучныеМатериалы', 'Файлы'} <= tables.keys())
        for name in ['Операции', 'Отверстия', 'СлоиПечати', 'Коннекторы', 'Файлы']:
            self.assertIn('Идентификатор', [c.findtext('name') for c in tables[name].findall('attributes')])
        material_fields = {c.findtext('name'): c for c in tables['Материалы'].findall('attributes')}
        self.assertEqual(material_fields['Корректировка'].findtext('type/numberQualifiers/nonNegative'), 'false')
        self.assertIn('ОснованиеРасчета', material_fields)

    def test_all_form_bindings_resolve_against_the_catalog(self):
        for catalog in ['Расш1_ТехническиеЛисты', 'Расш1_ОперацииТЛ', 'Расш1_ПравилаМатериаловТЛ']:
            folder = ROOT / 'Catalogs' / catalog
            metadata = ET.parse(folder / (catalog + '.mdo')).getroot()
            fields = {a.findtext('name') for a in metadata.findall('attributes')}
            tables = {t.findtext('name'): {a.findtext('name') for a in t.findall('attributes')}
                      for t in metadata.findall('tabularSections')}
            form = ET.parse(folder / 'Forms/ФормаЭлемента/Form.form').getroot()
            attrs = {a.findtext('name') for a in form.findall('attributes')}
            for control in form.iter('items'):
                path = control.findtext('dataPath/segments')
                if not path:
                    continue
                parts = path.split('.')
                self.assertIn(parts[0], attrs, path)
                if parts[0] == 'Объект' and len(parts) == 2:
                    self.assertIn(parts[1], fields | tables.keys() | {'Description', 'Code'}, path)
                elif parts[0] == 'Объект' and len(parts) == 3:
                    self.assertIn(parts[2], tables[parts[1]], path)
            # Command bars and controls share a namespace of UI element IDs.
            nodes = [n for n in form.iter() if n.tag in {'items', 'autoCommandBar'}]
            ids = [n.findtext('id') for n in nodes]
            names = [n.findtext('name') for n in nodes]
            self.assertEqual(len(ids), len(set(ids)), catalog)
            self.assertEqual(len(names), len(set(names)), catalog)

    def test_form_callbacks_and_server_events_have_compatible_signatures(self):
        contexts = {'OnCreateAtServer': ('НаСервере', 2), 'AfterWriteAtServer': ('НаСервере', 2),
                    'OnReadAtServer': ('НаСервере', 1), 'OnChange': ('НаКлиенте', 1),
                    'AfterDeleteRow': ('НаКлиенте', 1), 'OnStartEdit': ('НаКлиенте', 3)}
        for form_path in ROOT.glob('Catalogs/Расш1_*/Forms/*/Form.form'):
            code = form_path.with_name('Module.bsl').read_text(encoding='utf-8-sig')
            form = ET.parse(form_path).getroot()
            for handler in form.iter('handlers'):
                event, name = handler.findtext('event'), handler.findtext('name')
                context, argc = contexts[event]
                match = re.search(r'&' + context + r'\s+(?:Асинх\s+)?Процедура\s+' + name + r'\(([^)]*)\)', code)
                self.assertIsNotNone(match, name)
                self.assertEqual(len(match.group(1).split(',')), argc, name)
            for command in form.findall('formCommands'):
                name = command.findtext('action/handler/name')
                self.assertRegex(code, r'&НаКлиенте\s+(?:Асинх\s+)?Процедура\s+' + name + r'\(Команда\)')

    def test_automatic_and_manual_materials_are_edited_separately(self):
        form = ET.parse(FORM).getroot()
        controls = {n.findtext('name'): n for n in form.iter('items')}
        self.assertEqual(controls['Материалы'].findtext('changeRowSet'), 'false')
        self.assertEqual(controls['РучныеМатериалы'].findtext('changeRowSet'), 'true')
        for field in ['Номенклатура', 'Характеристика', 'Количество', 'Рассчитано', 'Правило', 'ОснованиеРасчета']:
            self.assertEqual(controls['Материалы' + field].findtext('readOnly'), 'true')
        self.assertEqual(controls['МатериалыКорректировка'].findtext('readOnly'), 'false')
        for field in ['Номенклатура', 'Характеристика', 'Количество']:
            self.assertEqual(controls['РучныеМатериалы' + field].findtext('readOnly'), 'false')

    def test_editable_input_fields_enable_keyboard_text_input(self):
        for path in ROOT.glob('Catalogs/Расш1_*/Forms/*/Form.form'):
            for field in ET.parse(path).getroot().iter('items'):
                if field.findtext('type') == 'InputField' and field.findtext('readOnly') != 'true':
                    self.assertEqual(field.findtext('extInfo/textEdit'), 'true',
                                     f'{path}: {field.findtext("name")}')
        form = ET.parse(FORM).getroot()
        name = next(f for f in form.iter('items') if f.findtext('name') == 'Наименование')
        self.assertEqual(name.findtext('readOnly'), 'false')
        self.assertEqual(name.findall('handlers'), [])

    def test_technology_card_uses_tabs_and_compact_groups(self):
        form = ET.parse(FORM).getroot()
        controls = {n.findtext('name'): n for n in form.iter('items')}
        pages = controls['СтраницыТехЛиста']
        self.assertEqual(pages.findtext('extInfo/pagesRepresentation'), 'TabsOnTop')
        self.assertTrue(all(p.findtext('type') == 'Page' for p in pages.findall('items')))
        header = controls['ШапкаТехЛиста']
        self.assertEqual(header.findtext('extInfo/group'), 'Vertical')
        self.assertEqual(header.findtext('verticalStretch'), 'false')
        self.assertEqual(header.findtext('extInfo/representation'), 'None')
        for group in form.iter('items'):
            if group.findtext('type') == 'UsualGroup':
                self.assertEqual(group.findtext('extInfo/representation'), 'None')
        self.assertEqual(controls['СообщениеРасчета'].findtext('titleLocation'), 'None')
        self.assertEqual(controls['СообщениеРасчета'].findtext('visible'), 'false')

    def test_required_identity_is_checked_on_the_server_before_allocating_a_revision(self):
        metadata = ET.parse(DIR / (NAME + '.mdo')).getroot()
        description = next(a for a in metadata.findall('standardAttributes') if a.findtext('name') == 'Description')
        product = next(a for a in metadata.findall('attributes') if a.findtext('name') == 'Номенклатура')
        self.assertEqual(description.findtext('fillChecking'), 'ShowError')
        self.assertEqual(product.findtext('fillChecking'), 'ShowError')
        self.assertEqual(ET.parse(FORM).getroot().findtext('autoFillCheck'), 'true')
        code = (ROOT / 'CommonModules/Расш1_ТехническиеЛистыСервер/Module.bsl').read_text()
        write = re.search(r'Процедура ПередЗаписьюТехЛиста\(Объект\).*?КонецПроцедуры', code, re.S).group()
        self.assertIn('ПроверитьОсновныеРеквизиты(Объект)', write)
        self.assertLess(write.index('ПроверитьОсновныеРеквизиты(Объект)'), write.index('НазначитьРедакцию(Объект)'))
        self.assertNotIn('ОбменДанными.Загрузка', write)
        check = re.search(r'Процедура ПроверитьОсновныеРеквизиты\(Объект\).*?КонецПроцедуры', code, re.S).group()
        self.assertIn('Если НЕ Объект.ЭтоНовый() И Объект.ПометкаУдаления Тогда', check)
        self.assertIn('Объект.Номенклатура.ПолучитьОбъект()', check)
        self.assertIn('Расш1_ПроверкаТЛ.ОшибкиОбязательныхПолей(Объект.Наименование', check)
        self.assertIn('ВызватьИсключение СтрСоединить(Ошибки, Символы.ПС)', check)

    def test_read_only_roles_cannot_write_technology_or_revision_counter(self):
        for role in ['Оператор', 'Контролер']:
            rights = all_rights(role)
            for catalog in ['Расш1_ТехническиеЛисты', 'Расш1_ПравилаМатериаловТЛ', 'Расш1_ОперацииТЛ']:
                self.assertEqual(rights['Catalog.' + catalog], {'Read', 'View'})
            self.assertNotIn('InformationRegister.Расш1_РедакцииТЛ', rights)
        for role in ['Расш1_Технолог', 'Мастер']:
            rights = all_rights(role)
            self.assertTrue({'Read', 'Insert', 'Update'} <= rights['Catalog.' + NAME])
            self.assertEqual(rights['InformationRegister.Расш1_РедакцииТЛ'], {'Read', 'Update'})

    def test_catalog_events_do_not_compile_server_calls_in_managed_client(self):
        for path in ROOT.glob('Catalogs/Расш1_*/ObjectModule.bsl'):
            code = path.read_text(encoding='utf-8-sig').strip()
            guard = re.match(r'#Если\s+(.+)\s+Тогда\s*\n', code)
            self.assertIsNotNone(guard, str(path))
            self.assertEqual(set(re.split(r'\s+Или\s+', guard.group(1))),
                             {'Сервер', 'ТолстыйКлиентОбычноеПриложение', 'ВнешнееСоединение'})
            self.assertTrue(code.endswith('#КонецЕсли'))
            self.assertRegex(code, r'Процедура ПередЗаписью\(Отказ\)')
        code = (DIR / 'ObjectModule.bsl').read_text(encoding='utf-8-sig')
        self.assertRegex(code, r'Процедура ПередУдалением\(Отказ\)')
        self.assertRegex(code, r'Процедура ПриКопировании\(ОбъектКопирования\)')

    def test_print_schema_only_contains_existing_catalog_fields(self):
        code = (ROOT / 'CommonModules/Расш1_СхемаТЛСервер/Module.bsl').read_text(encoding='utf-8-sig')
        metadata = ET.parse(DIR / (NAME + '.mdo')).getroot()
        fields = {a.findtext('name') for a in metadata.findall('attributes')}
        for csv in re.findall(r'\n\s*"([А-Яа-яЁёA-Za-z0-9_,]+)"\)\);', code):
            self.assertTrue(set(csv.split(',')) <= fields)

    def test_adopted_unf_objects_use_the_actual_user_supplied_uuids_and_types(self):
        contract = json.loads((ROOT.parents[1] / 'tests/fixtures/unf-specification-contract.json').read_text())
        metadata = ET.parse(ROOT / 'Catalogs/Спецификации/Спецификации.mdo').getroot()
        source = contract['catalog']
        self.assertEqual(metadata.get('extendedConfigurationObject'), source['uuid'])
        self.assertEqual(metadata.findtext('objectBelonging'), 'Adopted')
        tables = {t.findtext('name'): t for t in metadata.findall('tabularSections')}
        for part in ['composition', 'operations']:
            spec = source[part]
            table = tables[spec['name']]
            self.assertEqual(table.get('extendedConfigurationObject'), spec['uuid'])
            fields = {f.findtext('name'): f for f in table.findall('attributes')}
            for name, field in spec['attributes'].items():
                self.assertEqual(fields[name].get('extendedConfigurationObject'), field['uuid'])
                actual_types = [n.text for n in fields[name].findall('extension/typeExtension/types/type')]
                if field.get('check_type_in_extension', True):
                    self.assertEqual(actual_types, field.get('types', [field.get('type')]))
                    if field.get('type') == 'Number':
                        qualifiers = fields[name].find('extension/typeExtension/numberQualifiers')
                        self.assertIsNotNone(qualifiers)
                        self.assertEqual({n.tag: n.text for n in qualifiers}, {
                            'precision': str(field['precision']),
                            'scale': str(field['scale']),
                            'nonNegative': str(field['non_negative']).lower(),
                        })
                else:
                    self.assertEqual(fields[name].findtext('objectBelonging'), 'Adopted')
                    self.assertIsNone(fields[name].find('extension/type'))
                    self.assertIsNone(fields[name].find('extension/typeExtension'))
                    self.assertEqual(list(fields[name].find('type')), [])
            for name in ['Расш1_ИзТехЛиста', 'Расш1_КлючТехЛиста', 'Расш1_СнимокТехЛиста']:
                self.assertIsNone(fields[name].get('extendedConfigurationObject'))
        form = metadata.find('forms')
        self.assertEqual(form.get('extendedConfigurationObject'), source['form']['uuid'])
        enum = contract['composition_row_types']
        actual_enum = ET.parse(ROOT / f"Enums/{enum['name']}/{enum['name']}.mdo").getroot()
        self.assertEqual(actual_enum.get('extendedConfigurationObject'), enum['uuid'])
        material = actual_enum.find('enumValues')
        self.assertEqual(material.findtext('name'), 'Материал')
        self.assertEqual(material.get('extendedConfigurationObject'), enum['values']['Материал'])

    def test_composition_quantity_keeps_the_confirmed_unf_number_restrictions(self):
        # Параметры основной УНФ подтверждены скриншотом свойств Количество:
        # Число(15,3), неотрицательное. Одного имени типа Number недостаточно
        # для проверки совместимости заимствованного реквизита в платформе.
        metadata = ET.parse(ROOT / 'Catalogs/Спецификации/Спецификации.mdo').getroot()
        table = next(t for t in metadata.findall('tabularSections') if t.findtext('name') == 'Состав')
        quantity = next(a for a in table.findall('attributes') if a.findtext('name') == 'Количество')
        self.assertEqual(quantity.findtext('extension/type'), 'Checked')
        qualifiers = quantity.find('extension/typeExtension/numberQualifiers')
        self.assertEqual({n.tag: n.text for n in qualifiers}, {
            'precision': '15', 'scale': '3', 'nonNegative': 'true',
        })

    def test_native_form_hooks_match_confirmed_unf_events_and_dynamic_actions(self):
        folder = ROOT / 'Catalogs/Спецификации/Forms/ФормаЭлемента'
        code = (folder / 'Module.bsl').read_text()
        form = ET.parse(folder / 'Form.form').getroot()
        expected = {'OnCreateAtServer': 2, 'OnReadAtServer': 1,
                    'BeforeWriteAtServer': 3, 'AfterWriteAtServer': 2}
        handlers = {h.findtext('event'): h for h in form.iter('handlers')}
        self.assertEqual(set(handlers), set(expected))
        for event, count in expected.items():
            handler = handlers[event]
            self.assertEqual(handler.get('{http://www.w3.org/2001/XMLSchema-instance}type'),
                             'form:EventHandlerExtension')
            self.assertEqual(handler.findtext('callType'), 'After')
            name = handler.findtext('name')
            hook = re.search(r'&НаСервере\s+Процедура ' + name + r'\(([^)]*)\)', code)
            self.assertIsNotNone(hook, name)
            self.assertEqual(len(hook.group(1).split(',')), count)
        self.assertNotIn('&После(', code)  # Не вызывать обработчик повторно через аннотацию.
        helper = (ROOT / 'CommonModules/Расш1_ФормаСпецификацииТЛСервер/Module.bsl').read_text()
        for handler in re.findall(r'УстановитьДействие\("[^"]+", "([^"]+)"\)', helper):
            self.assertRegex(code, r'&НаКлиенте\s+(?:Асинх\s+)?Процедура ' + handler + r'\(')
        for command in re.findall(r'Новый Структура\("Имя,Заголовок", "([^"]+)"', helper):
            self.assertRegex(code, r'&НаКлиенте\s+(?:Асинх\s+)?Процедура ' + command + r'\(Команда\)')
        # Не терять дополнительные колонки при конвертации главного реквизита.
        self.assertNotRegex(code, r'ЗначениеВРеквизитФормы\([^;]+, "Объект"\)')

    def test_adopted_form_declares_managed_context_and_a_matching_base(self):
        folder = ROOT / 'Catalogs/Спецификации/Forms/ФормаЭлемента'
        form = ET.parse(folder / 'Form.form').getroot()
        base = ET.parse(folder / 'BaseForm/Form.form').getroot()
        xsi = '{http://www.w3.org/2001/XMLSchema-instance}type'
        self.assertEqual(form.find('extInfo').get(xsi), 'form:CatalogFormExtInfo')
        obj = next(a for a in form.findall('attributes') if a.findtext('name') == 'Объект')
        self.assertEqual(obj.findtext('main'), 'true')
        self.assertEqual(obj.findtext('valueType/types'), 'CatalogObject.Спецификации')
        metadata = ET.parse(ROOT / 'Catalogs/Спецификации/Спецификации.mdo').getroot()
        self.assertEqual(metadata.findtext('forms/extension/form'), 'Extended')
        # Статические свойства/реквизиты исходного и расширенного контекста
        # совпадают. В декларативной разнице остаются только события After.
        for tree in [form, base]:
            for node in tree.iter():
                for handler in list(node.findall('handlers')):
                    node.remove(handler)

        def normalized(node):
            return node.tag, tuple(sorted(node.attrib.items())), (node.text or '').strip(), tuple(map(normalized, node))

        self.assertEqual(normalized(form), normalized(base))

    def test_catalog_form_modules_have_a_form_context_file(self):
        for path in ROOT.glob('Catalogs/*/Forms/*/Module.bsl'):
            self.assertTrue(path.with_name('Form.form').is_file(), str(path))

    def test_client_form_handlers_do_not_use_the_server_enumerations_manager(self):
        for path in ROOT.glob('Catalogs/*/Forms/*/Module.bsl'):
            code = path.read_text(encoding='utf-8-sig')
            for handler in re.finditer(r'&НаКлиенте\s+(?:Асинх\s+)?(?:Процедура|Функция)\s+(\w+).*?(?:КонецПроцедуры|КонецФункции)', code, re.S):
                self.assertNotRegex(handler.group(), r'\bПеречисления\s*\.', f'{path}: {handler.group(1)}')

    def test_native_subscription_resolves_to_a_server_handler(self):
        name = 'Расш1_СпецификацияТЛПередЗаписью'
        event = ET.parse(ROOT / f'EventSubscriptions/{name}/{name}.mdo').getroot()
        self.assertEqual(event.findtext('source/types'), 'CatalogObject.Спецификации')
        self.assertEqual(event.findtext('event'), 'BeforeWrite')
        _, module, handler = event.findtext('handler').split('.')
        code = (ROOT / f'CommonModules/{module}/Module.bsl').read_text()
        self.assertRegex(code, r'Процедура ' + handler + r'\(Источник, Отказ\) Экспорт')


if __name__ == '__main__':
    unittest.main()
