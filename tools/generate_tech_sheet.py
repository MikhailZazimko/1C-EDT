"""Генерирует собственные метаданные техлиста из tech_sheet_schema.py.

Запуск из корня репозитория: python3 tools/generate_tech_sheet.py
Модули BSL сохраняются. UUID5 стабильны между запусками и применяются только
к новым объектам расширения. Заимствование типовой УНФ этот скрипт не выполняет.
"""
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
import re
import sys
import tech_sheet_schema as schema

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'АРМ_для_КМК/src'
NAMESPACE = uuid.UUID('2e2ee3ce-bc61-4bdd-90b7-28b33598f775')
MD = 'http://g5.1c.ru/v8/dt/metadata/mdclass'
FORM = 'http://g5.1c.ru/v8/dt/form'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'
ET.register_namespace('xsi', XSI)
ET.register_namespace('mdclass', MD)
ET.register_namespace('form', FORM)


def uid(key):
    return str(uuid.uuid5(NAMESPACE, key))


def child(parent, name, value=None, **attrs):
    result = ET.SubElement(parent, name, attrs)
    if value is not None:
        result.text = str(value)
    return result


def save(path, root):
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space='  ')
    path.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n')


def title(parent, text, tag='synonym'):
    node = child(parent, tag)
    child(node, 'key', 'ru')
    child(node, 'value', text)


def value_type(parent, kind, tag='type'):
    node = child(parent, tag)
    primitives = {'Text': 'String', 'Key': 'String', 'URL': 'String', 'SignedNumber': 'Number', 'Integer': 'Number'}
    child(node, 'types', primitives.get(kind, kind))
    if kind in {'String', 'Text', 'Key', 'URL'}:
        q = child(node, 'stringQualifiers')
        child(q, 'length', {'Text': 0, 'String': 200, 'Key': 250, 'URL': 1000}[kind])
    if kind in {'Number', 'Integer', 'SignedNumber'}:
        q = child(node, 'numberQualifiers')
        child(q, 'precision', 9 if kind == 'Integer' else 15)
        child(q, 'scale', 0 if kind == 'Integer' else 6)
        child(q, 'nonNegative', 'false' if kind == 'SignedNumber' else 'true')
    if kind == 'Date':
        child(child(node, 'dateQualifiers'), 'dateFractions', 'DateTime')
    return node


def fields(parent, specs, key):
    for name, label, kind in specs:
        field = child(parent, 'attributes', uuid=uid(key + '.' + name))
        child(field, 'name', name)
        title(field, label)
        value_type(field, kind)
        if kind == 'Text':
            child(field, 'multiLine', 'true')


def produced(parent, name, register=False, enum=False):
    node = child(parent, 'producedTypes')
    kinds = ['ref', 'list', 'manager'] if enum else ['object', 'ref', 'selection', 'list', 'manager']
    if register:
        kinds = ['selection', 'list', 'manager', 'recordSet', 'recordKey', 'record', 'recordManager']
    for kind in kinds:
        child(node, kind + 'Type', typeId=uid(name + '.' + kind), valueTypeId=uid(name + '.' + kind + '.value'))


def catalog(name, label, specs, tables=None, form=True, predefined=None):
    node = ET.Element('{' + MD + '}Catalog', {'uuid': uid('Catalog.' + name)})
    produced(node, name)
    child(node, 'name', name)
    title(node, label)
    child(node, 'useStandardCommands', 'true')
    child(node, 'codeLength', 9)
    child(node, 'descriptionLength', 150)
    child(node, 'codeType', 'String')
    child(node, 'codeAllowedLength', 'Variable')
    child(node, 'checkUnique', 'true')
    child(node, 'autonumbering', 'true')
    child(node, 'defaultPresentation', 'AsDescription')
    child(node, 'editType', 'InDialog')
    child(node, 'dataLockControlMode', 'Managed')
    if form:
        child(node, 'defaultObjectForm', f'Catalog.{name}.Form.ФормаЭлемента')
        f = child(node, 'forms', uuid=uid(name + '.ФормаЭлемента'))
        child(f, 'name', 'ФормаЭлемента')
    if predefined:
        pre = child(node, 'predefined')
        for item_name, description in predefined:
            item = child(pre, 'items', id=uid(name + '.predefined.' + item_name))
            child(item, 'name', item_name)
            child(item, 'description', description)
    fields(node, specs, name)
    if name == 'Расш1_ТехническиеЛисты':
        description = child(node, 'standardAttributes')
        child(description, 'name', 'Description')
        child(description, 'fillChecking', 'ShowError')
        product = next(a for a in node.findall('attributes') if a.findtext('name') == 'Номенклатура')
        child(product, 'fillChecking', 'ShowError')
    for table, (caption, columns) in (tables or {}).items():
        ts = child(node, 'tabularSections', uuid=uid(name + '.' + table))
        types = child(ts, 'producedTypes')
        for kind in ['object', 'row']:
            child(types, kind + 'Type', typeId=uid(name + '.' + table + '.' + kind),
                  valueTypeId=uid(name + '.' + table + '.' + kind + '.value'))
        child(ts, 'name', table)
        title(ts, caption)
        fields(ts, columns, name + '.' + table)
    save(SRC / f'Catalogs/{name}/{name}.mdo', node)


class Card:
    def __init__(self, name, label, full=False):
        self.name, self.full = name, full
        self.next_id = 1
        self.root = ET.Element('{' + FORM + '}Form')
        title(self.root, label, 'title')
        self.bar = child(self.root, 'autoCommandBar')
        child(self.bar, 'name', 'ФормаКоманднаяПанель')
        child(self.bar, 'id', -1)
        child(self.bar, 'autoFill', 'false')
        self.commands = []
        self.button('ЗаписатьИЗакрыть', 'Записать и закрыть', 'Form.StandardCommand.WriteAndClose')
        self.button('Записать', 'Записать', 'Form.StandardCommand.Write')
        if full:
            for cmd, caption in [('ПересчитатьМатериалы', 'Пересчитать материалы'), ('Утвердить', 'Утвердить'),
                                 ('НоваяРедакция', 'Создать редакцию'), ('ИндивидуальныйЛист', 'Создать индивидуальный'),
                                 ('ПечатьТехЛиста', 'Печать техлиста'), ('ПрикрепитьФайл', 'Прикрепить файл'),
                                 ('СохранитьФайл', 'Сохранить файл')]:
                self.button(cmd, caption, 'Form.Command.' + cmd)
                self.commands.append((cmd, caption))

    def control(self, parent, kind, name, caption=None):
        node = child(parent, 'items', **{'{' + XSI + '}type': 'form:' + kind})
        child(node, 'name', name)
        child(node, 'id', self.next_id)
        self.next_id += 1
        child(node, 'visible', 'true')
        child(node, 'enabled', 'true')
        child(child(node, 'userVisible'), 'common', 'true')
        if caption is not None:
            title(node, caption, 'title')
        return node

    def button(self, name, label, command):
        node = self.control(self.bar, 'Button', name, label)
        child(node, 'commandName', command)
        child(node, 'representation', 'Auto')
        if name == 'ЗаписатьИЗакрыть':
            child(node, 'defaultButton', 'true')

    def group(self, parent, name, caption, kind='UsualGroup', direction='Vertical'):
        node = self.control(parent, 'FormGroup', name, caption or None)
        child(node, 'horizontalStretch', 'true')
        child(node, 'verticalStretch', 'true' if kind == 'Pages' else 'false')
        child(node, 'type', kind)
        extname = {'UsualGroup': 'UsualGroupExtInfo', 'Page': 'PageGroupExtInfo', 'Pages': 'PagesGroupExtInfo'}[kind]
        ext = child(node, 'extInfo', **{'{' + XSI + '}type': 'form:' + extname})
        if kind != 'Pages':
            child(ext, 'group', direction)
        if kind == 'UsualGroup':
            child(ext, 'representation', 'None')
            child(ext, 'united', 'true')
            child(ext, 'throughAlign', 'Auto')
        elif kind == 'Page':
            child(ext, 'showTitle', 'true')
        else:
            child(ext, 'pagesRepresentation', 'TabsOnTop')
        return node

    def field(self, parent, spec, table=None, readonly=False, event=True):
        name, caption, kind = spec
        path = 'Объект.' + (table + '.' if table else '') + name
        if not table and name == 'Наименование':
            path = 'Объект.Description'
        node = self.control(parent, 'FormField', (table or '') + name, caption)
        data = child(node, 'dataPath', **{'{' + XSI + '}type': 'form:DataPath'})
        child(data, 'segments', path)
        child(node, 'type', 'CheckBoxField' if kind == 'Boolean' else 'InputField')
        child(node, 'readOnly', str(readonly).lower())
        if not table:
            child(node, 'titleLocation', 'Right' if kind == 'Boolean' else 'Left')
        ext = child(node, 'extInfo', **{'{' + XSI + '}type': 'form:' + ('CheckBoxFieldExtInfo' if kind == 'Boolean' else 'InputFieldExtInfo')})
        if kind != 'Boolean':
            child(ext, 'textEdit', str(not readonly).lower())
            child(ext, 'textSize', 'Normal')
            child(ext, 'autoMaxWidth', 'true')
            child(ext, 'autoMaxHeight', 'true')
            if not table:
                child(ext, 'width', 14 if kind in {'Number', 'Integer', 'SignedNumber'} else 30)
                child(ext, 'horizontalStretch', 'true')
        if kind == 'Text':
            child(ext, 'multiLine', 'true')
            if not table:
                child(ext, 'height', 3)
        if event and not readonly and self.full and kind not in {'String', 'Text', 'Date'}:
            self.handler(node, 'OnChange', 'ПараметрыПриИзменении')
        if self.name == 'Расш1_ПравилаМатериаловТЛ' and name == 'ИсточникМатериала':
            self.handler(node, 'OnChange', 'ИсточникМатериалаПриИзменении')
        return node

    def fields_grid(self, parent, name, specs, columns=2, readonly=False):
        position = 0
        for index, spec in enumerate(specs):
            if spec[2] == 'Text':
                self.field(parent, spec, readonly=readonly or spec[0] in schema.READONLY)
                position = 0
                continue
            if position == 0:
                row = self.group(parent, name + 'Строка' + str(index), '', direction='AlwaysHorizontal')
            self.field(row, spec, readonly=readonly or spec[0] in schema.READONLY)
            position = (position + 1) % columns

    @staticmethod
    def handler(parent, event, name):
        handler = child(parent, 'handlers')
        child(handler, 'event', event)
        child(handler, 'name', name)

    def table(self, parent, name, caption, columns):
        table = self.control(parent, 'Table', name, caption)
        path = child(table, 'dataPath', **{'{' + XSI + '}type': 'form:DataPath'})
        child(path, 'segments', 'Объект.' + name)
        child(table, 'changeRowSet', 'false' if name == 'Материалы' else 'true')
        child(table, 'changeRowOrder', 'false' if name == 'Материалы' else 'true')
        child(table, 'autoMaxWidth', 'true')
        child(table, 'autoMaxHeight', 'true')
        child(table, 'horizontalStretch', 'true')
        child(table, 'verticalStretch', 'true')
        child(table, 'height', 8)
        bar = child(table, 'autoCommandBar')
        child(bar, 'name', name + 'КоманднаяПанель')
        child(bar, 'id', self.next_id)
        self.next_id += 1
        child(bar, 'autoFill', 'true')
        for spec in columns:
            if spec[0] in schema.TABLE_HIDDEN:
                continue
            ro = name == 'Материалы' and spec[0] != 'Корректировка'
            self.field(table, spec, name, readonly=ro)
        if name != 'Материалы':
            self.handler(table, 'AfterDeleteRow', 'ПараметрыПриИзменении')
            self.handler(table, 'OnStartEdit', 'ТаблицаПриНачалеРедактирования')

    def finish(self):
        for index, (name, caption) in enumerate(self.commands, 1):
            cmd = child(self.root, 'formCommands')
            child(cmd, 'name', name)
            title(cmd, caption, 'title')
            child(cmd, 'id', index)
            child(child(cmd, 'use'), 'common', 'true')
            action = child(cmd, 'action', **{'{' + XSI + '}type': 'form:FormCommandHandlerContainer'})
            child(child(action, 'handler'), 'name', name)
        self.handler(self.root, 'OnCreateAtServer', 'ПриСозданииНаСервере')
        obj = child(self.root, 'attributes')
        child(obj, 'name', 'Объект')
        child(obj, 'id', 1)
        value_type(obj, 'CatalogObject.' + self.name, 'valueType')
        for flag in ['view', 'edit']:
            child(child(obj, flag), 'common', 'true')
        child(obj, 'main', 'true')
        child(obj, 'savedData', 'true')
        if self.full:
            message = child(self.root, 'attributes')
            child(message, 'name', 'СообщениеРасчета')
            child(message, 'id', 2)
            value_type(message, 'Text', 'valueType')
            for flag in ['view', 'edit']:
                child(child(message, flag), 'common', 'true')
        child(self.root, 'group', 'Vertical')
        child(self.root, 'autoFillCheck', 'true')
        child(self.root, 'width', 110 if self.full else 75)
        child(self.root, 'enabled', 'true')
        ext = child(self.root, 'extInfo', **{'{' + XSI + '}type': 'form:CatalogFormExtInfo'})
        if self.full:
            self.handler(ext, 'AfterWriteAtServer', 'ПослеЗаписиНаСервере')
            self.handler(ext, 'OnReadAtServer', 'ПриЧтенииНаСервере')
        save(SRC / f'Catalogs/{self.name}/Forms/ФормаЭлемента/Form.form', self.root)


def append_existing(path, additions):
    text = path.read_text(encoding='utf-8')
    closing = text.rfind('</')
    fragments = []
    for tag, value in additions:
        fragment = f'  <{tag}>{value}</{tag}>'
        if fragment not in text:
            fragments.append(fragment + '\n')
    text = text[:closing] + ''.join(fragments) + text[closing:]
    path.write_bytes(text.replace('\n', '\r\n').encode('utf-8'))


def generate_rights():
    role = ET.Element('{' + MD + '}Role', {'uuid': uid('Role.Расш1_Технолог')})
    child(role, 'name', 'Расш1_Технолог')
    title(role, 'Технолог КМК')
    save(SRC / 'Roles/Расш1_Технолог/Расш1_Технолог.mdo', role)
    for name in ['Расш1_Технолог', 'Мастер', 'Оператор', 'Контролер']:
        path = SRC / f'Roles/{name}/Rights.rights'
        if path.exists():
            text = path.read_text(encoding='utf-8')
        else:
            text = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<Rights xmlns="http://v8.1c.ru/8.2/roles" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="Rights">\n'
                    '\t<setForNewObjects>false</setForNewObjects>\n'
                    '\t<setForAttributesByDefault>true</setForAttributesByDefault>\n'
                    '\t<independentRightsOfChildObjects>false</independentRightsOfChildObjects>\n</Rights>\n')
        permissions = {}
        editor = name in {'Расш1_Технолог', 'Мастер'}
        for catalog_name in ['Расш1_ТехническиеЛисты', 'Расш1_ОперацииТЛ', 'Расш1_ПравилаМатериаловТЛ', 'Расш1_ЦветаСтекол']:
            rights = ['Read', 'View']
            if editor:
                rights += ['Insert', 'Update', 'Edit', 'InteractiveInsert',
                           'InteractiveSetDeletionMark', 'InteractiveClearDeletionMark']
            permissions['Catalog.' + catalog_name] = rights
        permissions['Catalog.Спецификации'] = ['Read', 'View']
        if editor:
            permissions['Catalog.Спецификации'] += ['Insert', 'Update', 'Edit', 'InteractiveInsert']
        if editor:
            permissions['InformationRegister.Расш1_РедакцииТЛ'] = ['Read', 'Update']
        if name == 'Расш1_Технолог':
            for object_name in ['Catalog.Номенклатура', 'Catalog.ХарактеристикиНоменклатуры', 'Catalog.Участки',
                                'Document.ЗаказНаПроизводство']:
                permissions[object_name] = ['Read', 'View']
        for object_name, rights in permissions.items():
            pattern = r'\t<object>\s*<name>' + re.escape(object_name) + r'</name>.*?</object>\n'
            text = re.sub(pattern, '', text, flags=re.S)
            block = '\t<object>\n\t\t<name>' + object_name + '</name>\n'
            for right in rights:
                block += f'\t\t<right>\n\t\t\t<name>{right}</name>\n\t\t\t<value>true</value>\n\t\t</right>\n'
            block += '\t</object>\n'
            text = text.replace('</Rights>', block + '</Rights>')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace('\n', '\r\n').encode('utf-8'))


def generate():
    for name, values in schema.ENUMS.items():
        node = ET.Element('{' + MD + '}Enum', {'uuid': uid('Enum.' + name)})
        produced(node, name, enum=True)
        child(node, 'name', name)
        for code, label in values:
            item = child(node, 'enumValues', uuid=uid(name + '.' + code))
            child(item, 'name', code)
            title(item, label)
        save(SRC / f'Enums/{name}/{name}.mdo', node)

    tl_fields = schema.IDENTITY + [field for _, _, fields_ in schema.SECTIONS for field in fields_]
    catalog('Расш1_ТехническиеЛисты', 'Технические листы', tl_fields, schema.TABLES)
    catalog('Расш1_ОперацииТЛ', 'Операции технических листов', schema.OPERATION_FIELDS,
            predefined=schema.ENUMS['Расш1_ВидыОперацийТЛ'])
    catalog('Расш1_ПравилаМатериаловТЛ', 'Правила материалов операций', schema.RULE_FIELDS)
    colors = [('БЦ', 'БЦ'), ('ЗЕ', 'ЗЕ'), ('BEU', 'BEU'), ('BGO', 'BGO'), ('ВК', 'ВК'),
              ('СЕ', 'СЕ'), ('СК', 'СК'), ('ЧЕ', 'ЧЕ'), ('TopN', 'TopN'), ('К', 'К'), ('G', 'G'), ('НЭ', 'НЭ'), ('ST', 'ST')]
    catalog('Расш1_ЦветаСтекол', 'Цвета стекол', [], form=False, predefined=colors)

    card = Card('Расш1_ТехническиеЛисты', 'Технический лист', full=True)
    header = card.group(card.root, 'ШапкаТехЛиста', '')
    card.field(header, ('Наименование', 'Наименование', 'String'), event=False)
    primary = {'Номенклатура', 'Характеристика', 'Индивидуальный', 'БазовоеКоличество'}
    secondary = {'Заказ', 'НомерСтрокиЗаказа', 'Состояние', 'Редакция'}
    identity = {s[0]: s for s in schema.IDENTITY}
    card.fields_grid(header, 'ШапкаИзделие', [identity[n] for n in ['Номенклатура', 'Характеристика']])
    card.fields_grid(header, 'Редакция', [identity[n] for n in ['БазовоеКоличество', 'Состояние', 'Редакция']], columns=3)
    card.field(header, identity['Индивидуальный'])
    purpose = card.group(header, 'Назначение', '')
    card.fields_grid(purpose, 'Назначение', [identity[n] for n in ['Заказ', 'НомерСтрокиЗаказа']])
    message = card.control(card.root, 'FormField', 'СообщениеРасчета', '')
    path = child(message, 'dataPath', **{'{' + XSI + '}type': 'form:DataPath'})
    child(path, 'segments', 'СообщениеРасчета')
    child(message, 'type', 'LabelField')
    child(message, 'titleLocation', 'None')
    message.find('visible').text = 'false'
    child(message, 'readOnly', 'true')
    message_ext = child(message, 'extInfo', **{'{' + XSI + '}type': 'form:LabelFieldExtInfo'})
    child(message_ext, 'autoMaxHeight', 'true')
    child(message_ext, 'horizontalStretch', 'true')
    pages = card.group(card.root, 'СтраницыТехЛиста', '', 'Pages')
    for group, caption, fields_ in schema.SECTIONS:
        page = card.group(pages, 'Страница' + group, caption, 'Page')
        card.fields_grid(page, 'Параметры' + group, fields_)
        if group == 'Сверловка':
            card.table(page, 'Отверстия', *schema.TABLES['Отверстия'])
        if group == 'Печать':
            card.table(page, 'СлоиПечати', *schema.TABLES['СлоиПечати'])
    for table in ['Операции', 'Коннекторы', 'Материалы', 'РучныеМатериалы', 'Файлы']:
        caption, columns = schema.TABLES[table]
        page = card.group(pages, 'Страница' + table, caption, 'Page')
        card.table(page, table, caption, columns)
    info = card.group(pages, 'СведенияРедакции', 'Сведения о редакции', 'Page')
    card.fields_grid(info, 'Сведения', [f for f in schema.IDENTITY if f[0] not in primary | secondary | schema.HIDDEN], readonly=True)
    card.finish()
    for name, caption, fields_ in [
            ('Расш1_ОперацииТЛ', 'Операция технического листа', schema.OPERATION_FIELDS),
            ('Расш1_ПравилаМатериаловТЛ', 'Правило материалов операции', schema.RULE_FIELDS)]:
        form = Card(name, caption)
        form.field(form.root, ('Наименование', 'Наименование', 'String'), event=False)
        form.fields_grid(form.root, 'Реквизиты', fields_)
        form.finish()

    modules = ['Расш1_МатериалыТЛРасчет', 'Расш1_ТехническиеЛистыСервер', 'Расш1_ПечатьТЛСервер', 'Расш1_СхемаТЛСервер', 'Расш1_ПроверкаТЛ']
    for name in modules:
        module = ET.Element('{' + MD + '}CommonModule', {'uuid': uid('CommonModule.' + name)})
        child(module, 'name', name)
        for flag in ['server', 'externalConnection', 'clientOrdinaryApplication']:
            child(module, flag, 'true')
        save(SRC / f'CommonModules/{name}/{name}.mdo', module)
    lines = ['// Генерируется tools/generate_tech_sheet.py из tech_sheet_schema.py.',
             'Функция Разделы() Экспорт', '\tРезультат = Новый Массив;']
    for name, caption, fields_ in [('Сведения', 'Сведения о редакции', schema.IDENTITY)] + schema.SECTIONS:
        names = ','.join(f[0] for f in fields_ if f[0] not in schema.HIDDEN)
        lines += [f'\tРезультат.Добавить(Новый Структура("Заголовок,Поля", "{caption}",', f'\t\t"{names}"));']
    lines += ['\tВозврат Результат;', 'КонецФункции', '']
    path = SRC / 'CommonModules/Расш1_СхемаТЛСервер/Module.bsl'
    path.write_text('\n'.join(lines), encoding='utf-8')

    register_name = 'Расш1_РедакцииТЛ'
    register = ET.Element('{' + MD + '}InformationRegister', {'uuid': uid('InformationRegister.' + register_name)})
    produced(register, register_name, register=True)
    child(register, 'name', register_name)
    title(register, 'Нумерация редакций технических листов')
    child(register, 'dataLockControlMode', 'Managed')
    last = child(register, 'resources', uuid=uid(register_name + '.ПоследняяРедакция'))
    child(last, 'name', 'ПоследняяРедакция')
    value_type(last, 'Integer')
    series = child(register, 'dimensions', uuid=uid(register_name + '.ЛинияРедакций'))
    child(series, 'name', 'ЛинияРедакций')
    value_type(series, 'String')
    save(SRC / f'InformationRegisters/{register_name}/{register_name}.mdo', register)

    objects = [('catalogs', 'Catalog.' + n) for n in
               ['Расш1_ТехническиеЛисты', 'Расш1_ОперацииТЛ', 'Расш1_ПравилаМатериаловТЛ', 'Расш1_ЦветаСтекол']]
    objects += [('enums', 'Enum.' + n) for n in schema.ENUMS]
    objects += [('commonModules', 'CommonModule.' + n) for n in modules]
    objects += [('informationRegisters', 'InformationRegister.' + register_name)]
    objects += [('roles', 'Role.Расш1_Технолог')]
    generate_rights()
    append_existing(SRC / 'Configuration/Configuration.mdo', objects)
    append_existing(SRC / 'Subsystems/АРМ_КМК/АРМ_КМК.mdo',
                    [('content', value) for tag, value in objects if tag == 'catalogs'])
    import generate_specification_integration
    generate_specification_integration.generate(sys.modules[__name__])


if __name__ == '__main__':
    generate()
