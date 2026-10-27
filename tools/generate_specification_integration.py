"""Заимствование спецификации по подтверждённым UUID из основной УНФ.

Вызывается основным генератором. Контекст управляемой формы и BaseForm
необходимы EDT для компиляции модуля. Элементы техлиста добавляются программно.
"""
import json
import xml.etree.ElementTree as ET


def generate(api):
    source_contract = json.loads((api.ROOT / 'tests/fixtures/unf-specification-contract.json').read_text(encoding='utf-8'))
    contract = source_contract['catalog']
    ext_ns = 'http://g5.1c.ru/v8/dt/metadata/mdclass/extension'
    ET.register_namespace('mdclassExtension', ext_ns)
    child, uid, fields, save = api.child, api.uid, api.fields, api.save
    catalog = ET.Element('{' + api.MD + '}Catalog', {
        'uuid': uid('adopted.Catalog.Спецификации'), 'extendedConfigurationObject': contract['uuid'],
        'xmlns:mdclassExtension': ext_ns})
    api.produced(catalog, 'adopted.Спецификации')
    child(catalog, 'name', 'Спецификации')
    child(catalog, 'objectBelonging', 'Adopted')
    extension = child(catalog, 'extension', **{'{' + api.XSI + '}type': 'mdclassExtension:CatalogExtension'})
    child(extension, 'extendedConfigurationObject', 'Checked')
    fields(catalog, [('Расш1_ЭтоТехническийЛист', 'Технический лист', 'Boolean'),
                     ('Расш1_ТехническийЛист', 'Редакция технического листа', 'CatalogRef.Расш1_ТехническиеЛисты')],
           'Спецификации')
    characteristic = contract['characteristic']
    attr = child(catalog, 'attributes', uuid=uid('adopted.Spec.ХарактеристикаПродукции'),
                 extendedConfigurationObject=characteristic['uuid'])
    child(attr, 'name', characteristic['name'])
    child(attr, 'objectBelonging', 'Adopted')
    extension = child(attr, 'extension', **{'{' + api.XSI + '}type': 'mdclassExtension:BasicFeatureExtension'})
    child(extension, 'extendedConfigurationObject', 'Checked')
    child(extension, 'type', 'Checked')
    t = child(child(extension, 'typeExtension'), 'types')
    child(t, 'state', 'Checked')
    child(t, 'type', characteristic['type'])
    child(attr, 'type')
    for section in ['composition', 'operations']:
        source = contract[section]
        ts = child(catalog, 'tabularSections', uuid=uid('adopted.Spec.' + source['name']),
                   extendedConfigurationObject=source['uuid'])
        produced = child(ts, 'producedTypes')
        for kind in ['object', 'row']:
            child(produced, kind + 'Type', typeId=uid('adopted.Spec.' + source['name'] + '.' + kind),
                  valueTypeId=uid('adopted.Spec.' + source['name'] + '.' + kind + '.value'))
        child(ts, 'name', source['name'])
        child(ts, 'objectBelonging', 'Adopted')
        ext = child(ts, 'extension', **{'{' + api.XSI + '}type': 'mdclassExtension:MdObjectExtension'})
        child(ext, 'extendedConfigurationObject', 'Checked')
        for attr_name, attr_source in source['attributes'].items():
            attr = child(ts, 'attributes', uuid=uid('adopted.Spec.' + source['name'] + '.' + attr_name),
                         extendedConfigurationObject=attr_source['uuid'])
            child(attr, 'name', attr_name)
            child(attr, 'objectBelonging', 'Adopted')
            ext = child(attr, 'extension', **{'{' + api.XSI + '}type': 'mdclassExtension:BasicFeatureExtension'})
            child(ext, 'extendedConfigurationObject', 'Checked')
            # Единица измерения наследует тип основной УНФ. Контролируемый
            # состав ссылочных типов потребовал бы заимствования справочников
            # единиц, хотя собственных полей этих типов у расширения нет.
            if attr_source.get('check_type_in_extension', True):
                child(ext, 'type', 'Checked')
                type_extension = child(ext, 'typeExtension')
                for kind in attr_source.get('types', [attr_source.get('type')]):
                    t = child(type_extension, 'types')
                    child(t, 'state', 'Checked')
                    child(t, 'type', kind)
                if attr_source.get('type') == 'Number':
                    qualifiers = child(type_extension, 'numberQualifiers')
                    for key in ['precision', 'scale']:
                        child(qualifiers, key, attr_source[key])
            child(attr, 'type')
        fields(ts, [('Расш1_ИзТехЛиста', 'Из технического листа', 'Boolean'),
                    ('Расш1_КлючТехЛиста', 'Источник расчётной строки', 'Key'),
                    ('Расш1_СнимокТехЛиста', 'Контроль расчётной строки', 'Text')], 'Spec.' + source['name'])
    form = child(catalog, 'forms', uuid=uid('adopted.Spec.Form.ФормаЭлемента'),
                 extendedConfigurationObject=contract['form']['uuid'])
    child(form, 'name', 'ФормаЭлемента')
    child(form, 'objectBelonging', 'Adopted')
    ext = child(form, 'extension', **{'{' + api.XSI + '}type': 'mdclassExtension:BasicFormExtension'})
    child(ext, 'extendedConfigurationObject', 'Checked')
    child(ext, 'form', 'Extended')
    save(api.SRC / 'Catalogs/Спецификации/Спецификации.mdo', catalog)
    generate_form(api, contract['form'])

    enum_contract = source_contract['composition_row_types']
    name = enum_contract['name']
    enum = ET.Element('{' + api.MD + '}Enum', {
        'uuid': uid('adopted.Enum.' + name), 'extendedConfigurationObject': enum_contract['uuid'],
        'xmlns:mdclassExtension': ext_ns})
    api.produced(enum, 'adopted.' + name, enum=True)
    child(enum, 'name', name)
    child(enum, 'objectBelonging', 'Adopted')
    ext = child(enum, 'extension', **{'{' + api.XSI + '}type': 'mdclassExtension:EnumExtension'})
    child(ext, 'extendedConfigurationObject', 'Checked')
    value = child(enum, 'enumValues', uuid=uid('adopted.' + name + '.Материал'),
                  extendedConfigurationObject=enum_contract['values']['Материал'])
    child(value, 'name', 'Материал')
    child(value, 'objectBelonging', 'Adopted')
    ext = child(value, 'extension', **{'{' + api.XSI + '}type': 'mdclassExtension:MdObjectExtension'})
    child(ext, 'extendedConfigurationObject', 'Checked')
    save(api.SRC / f'Enums/{name}/{name}.mdo', enum)

    modules = ['Расш1_СпецификацииТЛСервер', 'Расш1_ФормаСпецификацииТЛСервер', 'Расш1_СоставТЛРасчет']
    for name in modules:
        module = ET.Element('{' + api.MD + '}CommonModule', {'uuid': uid('CommonModule.' + name)})
        child(module, 'name', name)
        for flag in ['server', 'externalConnection', 'clientOrdinaryApplication']:
            child(module, flag, 'true')
        save(api.SRC / f'CommonModules/{name}/{name}.mdo', module)
    name = 'Расш1_СпецификацияТЛПередЗаписью'
    event = ET.Element('{' + api.MD + '}EventSubscription', {'uuid': uid('EventSubscription.' + name)})
    child(event, 'name', name)
    child(child(event, 'source'), 'types', 'CatalogObject.Спецификации')
    child(event, 'event', 'BeforeWrite')
    child(event, 'handler', 'CommonModule.Расш1_СпецификацииТЛСервер.СпецификацияПередЗаписью')
    save(api.SRC / f'EventSubscriptions/{name}/{name}.mdo', event)
    api.append_existing(api.SRC / 'Configuration/Configuration.mdo',
                        [('catalogs', 'Catalog.Спецификации'), ('eventSubscriptions', 'EventSubscription.' + name),
                         ('enums', 'Enum.' + enum_contract['name'])]
                        + [('commonModules', 'CommonModule.' + n) for n in modules])


def generate_form(api, contract):
    """Описывает контекст и добавляет только четыре обработчика After.

    Базовый и расширенный контексты имеют одинаковые реквизиты, свойства
    и командную панель. Единственная декларативная разница — события.
    Типовые элементы не удаляются и не заменяются статической разметкой.
    """
    import copy
    child = api.child
    base = ET.Element('{' + api.FORM + '}Form')
    bar = child(base, 'autoCommandBar')
    child(bar, 'name', 'ФормаКоманднаяПанель')
    child(bar, 'id', -1)
    child(bar, 'autoFill', 'true')
    obj = child(base, 'attributes')
    child(obj, 'name', 'Объект')
    child(obj, 'id', 1)
    api.value_type(obj, 'CatalogObject.Спецификации', 'valueType')
    for flag in ['view', 'edit']:
        child(child(obj, flag), 'common', 'true')
    child(obj, 'main', 'true')
    child(obj, 'savedData', 'true')
    ext = child(base, 'extInfo', **{'{' + api.XSI + '}type': 'form:CatalogFormExtInfo'})
    for event, handler_name in contract['handlers'].items():
        parent = base if event == 'OnCreateAtServer' else ext
        handler = child(parent, 'handlers')
        child(handler, 'event', event)
        child(handler, 'name', handler_name)
    form = copy.deepcopy(base)
    for parent in [form, form.find('extInfo')]:
        for handler in parent.findall('handlers'):
            event = handler.findtext('event')
            handler.set('{' + api.XSI + '}type', 'form:EventHandlerExtension')
            handler.find('name').text = 'Расш1_ТЛ' + contract['handlers'][event]
            child(handler, 'callType', 'After')
    path = api.SRC / 'Catalogs/Спецификации/Forms/ФормаЭлемента'
    api.save(path / 'BaseForm/Form.form', base)
    api.save(path / 'Form.form', form)
