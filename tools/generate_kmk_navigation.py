"""Группы команд раздела «Производство КМК» в штатном меню 1С."""
import xml.etree.ElementTree as ET


GROUPS = [
    ('Расш1_КМКПроизводство', 'Производство', [
        'CommonCommand.Расш1_ЖурналЗаказовВРаботу',
        'Document.Выработка.StandardCommand.OpenList',
    ]),
    ('Расш1_КМКТехническиеЛисты', 'Технические листы', [
        'Catalog.Расш1_ТехническиеЛисты.StandardCommand.OpenList',
        'Catalog.Расш1_ОперацииТЛ.StandardCommand.OpenList',
        'Catalog.Расш1_ПравилаМатериаловТЛ.StandardCommand.OpenList',
        'Catalog.Расш1_ЦветаСтекол.StandardCommand.OpenList',
    ]),
    ('Расш1_КМКСправочники', 'Справочники', [
        'Catalog.Участки.StandardCommand.OpenList',
        'Catalog.Марки.StandardCommand.OpenList',
        'Catalog.Расценки.StandardCommand.OpenList',
        'Catalog.ПричиныПростоев.StandardCommand.OpenList',
    ]),
    ('Расш1_КМКНастройки', 'Настройки', [
        'InformationRegister.ДопускиСотрудников.StandardCommand.OpenList',
        'InformationRegister.Расш1_РаботникиПользователей.StandardCommand.OpenList',
    ]),
]


def generate(api):
    namespace = 'http://g5.1c.ru/v8/dt/cmi'
    ET.register_namespace('cmi', namespace)
    interface = ET.Element('{' + namespace + '}CommandInterface')
    placement = api.child(interface, 'commandsPlacement')
    order = api.child(interface, 'commandsOrder')
    references = []
    for name, caption, commands in GROUPS:
        group = ET.Element('{' + api.MD + '}CommandGroup', {'uuid': api.uid('CommandGroup.' + name)})
        api.child(group, 'name', name)
        api.title(group, caption)
        api.child(group, 'representation', 'Auto')
        api.child(group, 'category', 'NavigationPanel')
        api.save(api.SRC / f'CommandGroups/{name}/{name}.mdo', group)
        reference = 'CommandGroup.' + name
        references.append(('commandGroups', reference))
        for parent, fragment in [(placement, 'placementFragments'), (order, 'orderFragments')]:
            item = api.child(parent, fragment)
            api.child(item, 'group', reference)
            for command in commands:
                api.child(item, 'commands', command)
    # Доступность команд по ролям остаётся штатной; видимость не переопределяем.
    api.save(api.SRC / 'Subsystems/АРМ_КМК/CommandInterface.cmi', interface)
    api.append_existing(api.SRC / 'Configuration/Configuration.mdo', references)


if __name__ == '__main__':
    import generate_tech_sheet
    generate(generate_tech_sheet)
