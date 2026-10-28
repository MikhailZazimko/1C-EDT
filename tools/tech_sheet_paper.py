"""Компоновка экрана по одному листу предоставленного PDF, без данных образца."""
import tech_sheet_schema as schema

THICKNESSES = [('21', 2.1), ('22', 2.2), ('25', 2.5), ('26', 2.6), ('30', 3),
               ('32', 3.2), ('34', 3.4), ('35', 3.5), ('40', 4), ('50', 5),
               ('60', 6), ('80', 8), ('100', 10)]
COLORS = ['БЦ', 'ЗЕ', 'BEU', 'BGO', 'ВК', 'СЕ', 'СК', 'ЧЕ', 'TopN', 'К', 'G', 'НЭ', 'ST']
PIVOTS = [('Отверстия', 'Отверстие', 1), ('СлоиПечати', 'Слой', 3), ('Коннекторы', 'Коннектор', 4)]
IMAGE_ROLES = [('Чертёж', 'ЛистЧертеж'), ('Маркировка', 'ЛистМаркировка'),
               ('Фото изделия 1', 'ЛистФото1'), ('Фото изделия 2', 'ЛистФото2'),
               ('Фото изделия 3', 'ЛистФото3')]
ALIASES = {
    'ШиринаМм': 'Размер, мм', 'ВысотаМм': '×', 'ВидОбработкиСтекла': 'Тип годного изделия',
    'ПроизводительАвто': 'Производитель', 'МодельАвто': 'Модель', 'ГодыВыпуска': 'Год',
    'ПрипускРезкиМм': 'Припуск, мм', 'ДавлениеРолика': 'Давление ролика',
    'КоличествоВырезов': 'Вырезы', 'Проходов1': 'Проходов', 'Проходов2': 'Проходов',
    'Проходов3': 'Проходов', 'СнятьНаСторонуМм': 'Снять на сторону, мм',
    'ДопускГабаритаМм': 'Допуск габарита, мм', 'Примечание1': 'Пр1', 'Примечание2': 'Пр2',
    'Примечание3': 'Пр3', 'ПризнакШелкографии': 'Шелк', 'ПризнакЭлектрообогрева': 'Э/О',
    'СлойЭлектрообогрева': '№ слоя э/о', 'СопротивлениеОтОм': 'Сопротивление от, Ом',
    'СопротивлениеДоОм': 'до, Ом', 'ТолщинаНитиМм': 'Толщина нитей, мм',
    'ВремяНагреваСек': 'Время нагрева, с', 'ВремяЗакалкиСек': 'Время закалки, с',
    'ВремяОхлажденияСек': 'Время охлаждения, с', 'ДатаСоздания': 'Дата создания', 'Автор': 'ТЛ создал',
}
HOLE_FIELDS = {'Количество', 'ДиаметрМм', 'ДоКраяМм'}
PIVOT_CAPTIONS = {'ВидСлоя': 'Слой', 'Количество': 'Кол-во',
                  'КоличествоПаек': 'Паек на коннектор', 'ПроцентНанесения': '% нанесения'}
BLOCKS = [
    ('Резка', 'РЕЗКА', [
        ['СтолРезки', 'ТипРолика', 'ПрипускРезкиМм'],
        ['ФайлРезки', 'ДавлениеРолика', 'РазверткаЯчейка'],
        ['ОловоПокрытие', 'НомерПокрытия']]),
    ('ГАР', 'ГАР', [['ОборудованиеГАР'], ['ФайлГАР'], ['КоличествоДеталейГАР', 'ОтверстияГАР']]),
    ('Кромка', 'ОБРАБОТКА КРОМКИ', [
        ['ОбработкаТорцов', 'КоличествоВырезов', 'Инструмент1', 'Проходов1'],
        ['ЦентрОбработки', 'СнятьНаСторонуМм', 'Инструмент2', 'Проходов2'],
        ['ФайлКромки', 'ДопускГабаритаМм', 'Инструмент3', 'Проходов3'], ['РазверткаКромки']]),
    ('Сверловка', 'СВЕРЛОВКА', [
        ['СветитьСтекло', 'МерныйШаблон', 'ИспользованиеПланки'],
        ['ФайлСверловки', 'СтеллажСверловки', 'ПолкаСверловки', 'ТипЗамкаФорточки'],
        ['ПримечаниеСверловка']]),
    ('Маркировка', 'МАРКИРОВКА', [
        ['МестоМаркировки', 'ЧитаемостьМаркировки', 'ПозицияМаркировки'],
        ['ПоверхностьМаркировки', 'ПримечаниеМаркировка'], ['ОбразецМаркировки']]),
    ('Печать', 'ПЕЧАТЬ', [
        ['РежимСушки', 'СлойЭлектрообогрева', 'КоличествоНитей'],
        ['СветитьПриПечати', 'ИспользованиеЕлки', 'ТолщинаНитиМм'],
        ['СопротивлениеОтОм', 'СопротивлениеДоОм', 'ВидСоСтороны']]),
    ('Закалка', 'ЗАКАЛКА', [
        ['Печь', 'ФайлЗакалки'], ['ОбработкаЗакалка', 'ФормаСтекла', 'НаправлениеЗакалки'],
        ['Обдувки', 'АркаМм', 'РадиусМм', 'ЗагрузкаПечи'],
        ['ВремяНагреваСек', 'ВремяЗакалкиСек', 'ВремяОхлажденияСек'],
        ['ПоперечныйПровисМм', 'ДопускПрилеганияМм', 'ВыходЗакалки'],
        ['РабочаяОснастка', 'СтеллажОснастки', 'ПолкаОснастки'], ['ОбразецБирки']]),
    ('Контроль', 'КОНТРОЛЬ / УПАКОВКА', [
        ['КонтрольноеСтекло', 'РадиусКонтроляМм'], ['СтеллажКонтроля', 'ПолкаКонтроля'],
        ['УпаковкаСтекла', 'ПримечаниеКонтроль'], ['Комментарий']]),
]


def cells():
    for table, prefix, count in PIVOTS:
        for number in range(1, count + 1):
            for field, caption, kind in schema.TABLES[table][1]:
                if field not in schema.TABLE_HIDDEN:
                    if table == 'Отверстия' and field not in HOLE_FIELDS:
                        continue
                    yield f'Лист{prefix}{number}{field}', table, number, field, caption, kind


def generate(card, api):
    for table, prefix, count in PIVOTS:
        for index in range(1, count + 1):
            card.additional_attributes[f'ЛистИД{table}{index}'] = 'String'
    # Все поля данных сохраняют типы и пути исходной карточки.
    specs = {s[0]: s for s in schema.IDENTITY + [s for _, _, fields in schema.SECTIONS for s in fields]}
    specs['Наименование'] = ('Наименование', 'Наименование', 'String')
    used = set()
    number = 0

    def color(node, shade='Web.Gainsboro'):
        c = api.child(node, 'backColor', **{'{' + api.XSI + '}type': 'core:ColorRef'})
        api.child(c, 'color', shade)

    def label(parent, text, name=None, width=None):
        nonlocal number
        number += 1
        n = card.control(parent, 'Decoration', name or f'ЛистНадпись{number}', text)
        api.child(n, 'type', 'Label')
        ext = api.child(n, 'extInfo', **{'{' + api.XSI + '}type': 'form:LabelDecorationExtInfo'})
        font = api.child(ext, 'font', **{'{' + api.XSI + '}type': 'core:FontRef'})
        api.child(font, 'font', 'System.DefaultGUIFont')
        api.child(font, 'bold', 'true')
        if name == 'ЛистЗаголовок':
            api.child(font, 'scale', 160)
        if width:
            api.child(n, 'width', width)
            api.child(n, 'horizontalStretch', 'true' if width == 13 else 'false')
        return n

    def field(parent, key, caption=None):
        used.add(key)
        spec = specs[key]
        n = card.field(parent, (key, caption or ALIASES.get(key, spec[1]), spec[2]), readonly=key in schema.READONLY)
        ext = n.find('extInfo')
        if spec[2] != 'Boolean':
            ext.find('width').text = str(8 if spec[2] in ('Number', 'Integer') else 16)
            color(ext)
            if spec[2] == 'Text':
                ext.find('height').text = '2'
        return n

    def row(parent, keys):
        nonlocal number
        number += 1
        r = card.group(parent, f'ЛистСтрока{number}', '', direction='AlwaysHorizontal')
        for key in keys:
            field(r, key)
        return r

    def block(parent, key):
        _, caption, rows = next(b for b in BLOCKS if b[0] == key)
        b = card.group(parent, 'ЛистБлок' + key, caption)
        b.find('extInfo/representation').text = 'NormalSeparation'
        for keys in rows:
            row(b, keys)
        return b

    def pivot(parent, table):
        _, prefix, count = next(p for p in PIVOTS if p[0] == table)
        b = card.group(parent, 'ЛистМатрица' + prefix, '')
        if table == 'Отверстия':
            card.additional_attributes['ЛистКоличествоОтверстий'] = 'Integer'
            card.field(b, ('ЛистКоличествоОтверстий', 'Всего отверстий', 'Integer'), path='ЛистКоличествоОтверстий', readonly=True, event=False)
            r = card.group(b, 'ЛистПараметрыОтверстия', '', direction='AlwaysHorizontal')
            for key, caption, kind in schema.TABLES[table][1]:
                if key not in HOLE_FIELDS:
                    continue
                name = f'Лист{prefix}1{key}'
                card.additional_attributes[name] = kind
                n = card.field(r, (name, caption, kind), path=name, event=False)
                card.handler(n, 'OnChange', 'ЯчейкаЛистаПриИзменении')
                color(n.find('extInfo'))
            return
        if table == 'СлоиПечати':
            card.additional_attributes['ЛистКоличествоСлоев'] = 'Integer'
            card.field(b, ('ЛистКоличествоСлоев', 'Кол-во слоёв', 'Integer'), path='ЛистКоличествоСлоев', readonly=True, event=False)
        r = card.group(b, 'ЛистЗаголовки' + prefix, '', direction='AlwaysHorizontal')
        label(r, 'Поле', width=19)
        for index in range(1, count + 1):
            label(r, str(index), width=13)
        for key, caption, kind in schema.TABLES[table][1]:
            if key in schema.TABLE_HIDDEN:
                continue
            r = card.group(b, 'ЛистСтрока' + prefix + key, '', direction='AlwaysHorizontal')
            label(r, PIVOT_CAPTIONS.get(key, caption), width=19)
            for index in range(1, count + 1):
                name = f'Лист{prefix}{index}{key}'
                card.additional_attributes[name] = kind
                cell = card.group(r, 'ЛистМесто' + name, '')
                api.child(cell, 'width', 13)
                n = card.field(cell, (name, '', kind), path=name, event=False)
                n.find('titleLocation').text = 'None'
                card.handler(n, 'OnChange', 'ЯчейкаЛистаПриИзменении')
                ext = n.find('extInfo')
                if kind != 'Boolean':
                    ext.find('width').text = '13'
                    color(ext)
                    if kind == 'Text':
                        ext.find('height').text = '2'

    def picture(parent, name, caption, height, width=32):
        card.additional_attributes[name] = 'URL'
        n = card.control(parent, 'FormField', name, caption)
        p = api.child(n, 'dataPath', **{'{' + api.XSI + '}type': 'form:DataPath'})
        api.child(p, 'segments', name)
        api.child(n, 'type', 'PictureField')
        api.child(n, 'readOnly', 'true')
        ext = api.child(n, 'extInfo', **{'{' + api.XSI + '}type': 'form:ImageFieldExtInfo'})
        api.child(ext, 'width', width)
        api.child(ext, 'height', height)
        api.child(ext, 'horizontalStretch', 'false' if name == 'ЛистМаркировка' else 'true')
        api.child(ext, 'pictureSize', 'AutoSize')
        api.title(ext, caption + ': прикрепите изображение на вкладке «Файлы»', 'nonselectedPictureText')

    pages = card.group(card.root, 'СтраницыТехЛиста', '', 'Pages')
    sheet = card.group(pages, 'СтраницаЛист', 'Технический лист', 'Page')
    title_row = card.group(sheet, 'ЛистНазвание', '', direction='AlwaysHorizontal')
    label(title_row, 'КМК GLASS', 'ЛистМарка', width=15)
    label(title_row, 'ТЕХНИЧЕСКИЙ ЛИСТ', 'ЛистЗаголовок')
    header = card.group(sheet, 'ШапкаТехЛиста', '')
    row(header, ['Цех', 'КодИзделия', 'ВидОбработкиСтекла', 'СвязанноеСтекло'])
    row(header, ['Наименование', 'Номенклатура', 'Характеристика'])
    row(header, ['ТипТранспорта', 'ПроизводительАвто', 'МодельАвто', 'Кузов', 'ГодыВыпуска'])
    row(header, ['ТипСтекла', 'ШиринаМм', 'ВысотаМм', 'ОписаниеИзделия', 'Сторона'])
    for category, values in [('Толщина', THICKNESSES), ('Цвет', [(c, c) for c in COLORS])]:
        r = card.group(sheet, 'ЛистШкала' + category, '', direction='AlwaysHorizontal')
        label(r, category.upper(), width=12)
        for code, value in values:
            name = 'ЛистВыбор' + category + code
            card.additional_attributes[name] = 'Boolean'
            caption = f'{value:.1f}'.replace('.', ',') if category == 'Толщина' else str(value)
            n = card.field(r, (name, caption, 'Boolean'), path=name, event=False)
            card.handler(n, 'OnChange', 'ЯчейкаЛистаПриИзменении')
        field(r, 'ТолщинаМм' if category == 'Толщина' else 'ЦветСтекла', 'Другое')
    row(sheet, ['Примечание1', 'СМ2', 'ПризнакШелкографии', 'ПризнакФорточки'])
    row(sheet, ['Примечание2', 'ПризнакЭлектрообогрева', 'ПризнакАнтенны'])
    row(sheet, ['Примечание3', 'РазмерСклада', 'РазмерСкладаПримечание'])
    cutting = card.group(sheet, 'ЛистРезкаГАР', '', direction='AlwaysHorizontal')
    api.child(block(cutting, 'Резка'), 'width', 75)
    api.child(block(cutting, 'ГАР'), 'width', 38)
    block(sheet, 'Кромка')
    drilling = block(sheet, 'Сверловка')
    pivot(drilling, 'Отверстия')
    marking_row = card.group(sheet, 'ЛистМаркировкаСПробой', '', direction='AlwaysHorizontal')
    block(marking_row, 'Маркировка')
    picture(marking_row, 'ЛистМаркировка', 'Образец маркировки', 5, width=14)
    lower = card.group(sheet, 'ЛистНижняяЧасть', '', direction='AlwaysHorizontal')
    technology = card.group(lower, 'ЛистТехнология', '')
    api.child(technology, 'width', 75)
    printing = block(technology, 'Печать')
    pivot(printing, 'СлоиПечати')
    block(technology, 'Закалка')
    block(technology, 'Контроль')
    soldering = card.group(technology, 'ЛистБлокПайка', 'ПАЙКА')
    soldering.find('extInfo/representation').text = 'NormalSeparation'
    pivot(soldering, 'Коннекторы')
    row(soldering, ['ПримечаниеПайка'])
    images = card.group(lower, 'ЛистИллюстрации', '')
    api.child(images, 'width', 38)
    for name, caption, height in [('ЛистЧертеж', 'Чертёж изделия', 15),
                                   ('ЛистФото1', 'Фото изделия 1', 12)]:
        picture(images, name, caption, height)
    pair = card.group(images, 'ЛистПарныеФото', '', direction='AlwaysHorizontal')
    picture(pair, 'ЛистФото2', 'Фото изделия 2', 10, width=16)
    picture(pair, 'ЛистФото3', 'Фото изделия 3', 10, width=16)
    row(sheet, ['Автор', 'ДатаСоздания', 'Утвердил', 'ДатаУтверждения'])
    # Поля расчёта, отсутствующие в бумажном образце, собраны отдельно.
    calculation = card.group(pages, 'СтраницаРасчет', 'Маршрут и материалы', 'Page')
    row(calculation, ['БазовоеКоличество', 'Состояние', 'Редакция', 'Индивидуальный'])
    purpose = card.group(calculation, 'Назначение', '')
    row(purpose, ['Заказ', 'НомерСтрокиЗаказа'])
    remaining = [s for s in specs.values() if s[0] not in used | schema.HIDDEN | schema.READONLY]
    card.fields_grid(calculation, 'Расчет', remaining)
    for table in ['Операции', 'Материалы', 'РучныеМатериалы']:
        card.table(calculation, table, *schema.TABLES[table])
    details = card.group(pages, 'СтраницаТаблицы', 'Слои, отверстия, коннекторы', 'Page')
    for table in ['СлоиПечати', 'Отверстия', 'Коннекторы']:
        card.table(details, table, *schema.TABLES[table])
    files = card.group(pages, 'СтраницаФайлы', 'Файлы', 'Page')
    card.table(files, 'Файлы', *schema.TABLES['Файлы'])
    info = card.group(pages, 'СведенияРедакции', 'Сведения о редакции', 'Page')
    card.fields_grid(info, 'Сведения', [s for s in schema.IDENTITY if s[0] in schema.READONLY and s[0] not in used | schema.HIDDEN], readonly=True)
    return pages
