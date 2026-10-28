"""Создаёт браузерную схему компоновки из сгенерированной формы 1С."""
from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / 'АРМ_для_КМК/src/Catalogs/Расш1_ТехническиеЛисты/Forms/ФормаЭлемента/Form.form'


def render(node):
    name = node.findtext('name', '')
    caption = escape(node.findtext('title/value', ''))
    kind = node.findtext('type')
    if kind == 'UsualGroup' or kind == 'Page':
        direction = node.findtext('extInfo/group')
        classes = ['row' if direction == 'AlwaysHorizontal' else 'stack']
        if node.findtext('extInfo/representation') == 'NormalSeparation':
            classes.append('block')
        if name.startswith('ЛистШкала'):
            classes.append('scale')
        classes.append(name)
        title = f'<h3>{caption}</h3>' if caption and 'block' in classes else ''
        return f'<section class="{" ".join(classes)}">{title}' + ''.join(render(n) for n in node.findall('items')) + '</section>'
    if kind == 'Label':
        width = node.findtext('width')
        flex = '1 1' if width == '13' else '0 0'
        style = f' style="flex:{flex} {int(width)}ch"' if width else ''
        return f'<span class="label {name}"{style}>{caption}</span>'
    if kind == 'PictureField':
        height = int(node.findtext('extInfo/height', '10')) * 12
        return f'<div class="picture" style="height:{height}px">{caption}</div>'
    if kind in ('InputField', 'CheckBoxField'):
        label = f'<span>{caption}</span>' if caption else ''
        ro = ' readonly' if node.findtext('readOnly') == 'true' else ''
        if kind == 'CheckBoxField':
            return f'<label class="check"><input type="checkbox">{label}</label>'
        if node.findtext('extInfo/multiLine') == 'true':
            control = f'<textarea rows="2"{ro}></textarea>'
        else:
            control = f'<input type="text"{ro}>'
        return f'<label class="field">{label}{control}</label>'
    return ''


def generate():
    tree = ET.parse(FORM).getroot()
    page = next(n for n in tree.iter('items') if n.findtext('name') == 'СтраницаЛист')
    css = '''*{box-sizing:border-box}body{margin:0;padding:24px;background:#ececec;color:#111;font:12px Arial,sans-serif}
main{max-width:1280px;margin:auto;background:white;padding:22px;border:1px solid #aaa}p.note{max-width:1280px;margin:0 auto 16px;color:#555}
.row{display:flex;gap:6px;align-items:center;min-width:0}.stack{display:flex;flex-direction:column;gap:5px;min-width:0;flex:1}
.row>section{flex:1}.block{border:1px solid #202020;padding:5px;gap:5px}h3{font-size:13px;margin:0 0 2px;font-weight:700}
.field{display:flex;gap:4px;align-items:center;flex:1;min-width:0}.field>span{flex:0 1 auto;max-width:50%;line-height:1.1}
.field input,.field textarea{border:0;border-bottom:1px solid #aaa;background:#d5d5d5;color:#111;font:12px Arial;padding:3px;width:100%;min-width:20px;flex:1}
.field textarea{resize:vertical;min-height:28px}.check{display:flex;align-items:center;gap:2px;white-space:nowrap;font-size:11px}.check input{margin:0;width:12px;height:12px}
.label{font-weight:bold;flex:1;min-width:0}.scale{border:1px solid #222;padding:5px 3px;gap:4px}.scale .field{max-width:180px}
.ЛистНазвание{padding:8px 0}.ЛистЗаголовок{font-size:26px}.ЛистМарка{font-size:18px}.ШапкаТехЛиста{border:1px solid #222;padding:5px}
.ЛистНижняяЧасть{align-items:stretch}.ЛистНижняяЧасть>.ЛистТехнология{flex:6}.ЛистНижняяЧасть>.ЛистИллюстрации{flex:4}
.ЛистРезкаГАР>.ЛистБлокРезка{flex:7}.ЛистРезкаГАР>.ЛистБлокГАР{flex:3}
.picture{border:1px solid #bbb;display:flex;align-items:center;justify-content:center;color:#666;background:#fafafa;flex:1;min-width:0}
.ЛистМаркировкаСПробой>.picture{max-width:145px}.ЛистИллюстрации{justify-content:space-around;padding:6px}.ЛистПарныеФото{align-items:stretch}
@media(max-width:900px){body{padding:6px}main{min-width:1100px;padding:12px}}@media print{body{padding:0;background:white}.note{display:none}main{border:0;padding:0}}
'''
    html = '<!doctype html><html lang="ru"><meta charset="utf-8"><title>Техлист — схема карточки 1С</title><style>' + css + '</style>'
    html += '<p class="note">Предпросмотр расположения полей карточки 1С по вашему PDF. Шрифты и размеры элементов в 1С зависят от платформы и масштаба интерфейса. Данные здесь не записываются в базу.</p><main>'
    html += render(page) + '</main></html>'
    target = ROOT / 'docs/tech-sheet-paper-preview.html'
    target.write_text(html, encoding='utf-8')


if __name__ == '__main__':
    generate()
