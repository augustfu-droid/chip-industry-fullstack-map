#!/usr/bin/env python3
"""Render every PDF page, build contact sheets, and run structural checks."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / '芯片产业链全栈技术图谱_公开版.md'
VERSION_MATCH = re.search(
    r'^>\s*版本\s+([^·\s]+)',
    REPORT.read_text(encoding='utf-8'),
    re.MULTILINE,
)
if VERSION_MATCH is None:
    raise RuntimeError(f'无法从报告元数据读取版本号：{REPORT}')
REPORT_VERSION = VERSION_MATCH.group(1)
DEFAULT_PDF = ROOT / 'output' / 'pdf' / f'芯片产业链全栈技术图谱_公开版_{REPORT_VERSION}.pdf'
DEFAULT_OUTPUT = ROOT / 'tmp' / 'pdfs' / 'qa'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', nargs='?', type=Path, default=DEFAULT_PDF)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--pdftoppm', default='pdftoppm')
    parser.add_argument('--dpi', type=int, default=90)
    return parser.parse_args()


def render_pages(pdf_path: Path, pages_dir: Path, pdftoppm: str, dpi: int) -> list[Path]:
    pages_dir.mkdir(parents=True, exist_ok=True)
    for old_image in pages_dir.glob('page-*.jpg'):
        old_image.unlink()
    subprocess.run(
        [
            pdftoppm,
            '-jpeg',
            '-jpegopt',
            'quality=84,optimize=y',
            '-r',
            str(dpi),
            str(pdf_path),
            str(pages_dir / 'page'),
        ],
        check=True,
    )
    return sorted(pages_dir.glob('page-*.jpg'))


def build_contact_sheets(page_images: list[Path], output_dir: Path) -> list[Path]:
    sheets_dir = output_dir / 'contact-sheets'
    if sheets_dir.exists():
        shutil.rmtree(sheets_dir)
    sheets_dir.mkdir(parents=True)

    columns = 4
    rows = 4
    thumb_width = 240
    thumb_height = 340
    label_height = 24
    margin = 16
    per_sheet = columns * rows
    sheet_paths = []

    for sheet_index in range(0, len(page_images), per_sheet):
        batch = page_images[sheet_index:sheet_index + per_sheet]
        canvas = Image.new(
            'RGB',
            (
                columns * (thumb_width + margin) + margin,
                rows * (thumb_height + label_height + margin) + margin,
            ),
            'white',
        )
        draw = ImageDraw.Draw(canvas)
        for index, image_path in enumerate(batch):
            page_number = sheet_index + index + 1
            row, column = divmod(index, columns)
            x = margin + column * (thumb_width + margin)
            y = margin + row * (thumb_height + label_height + margin)
            with Image.open(image_path) as image:
                thumb = ImageOps.contain(image.convert('RGB'), (thumb_width, thumb_height))
                offset_x = x + (thumb_width - thumb.width) // 2
                offset_y = y + (thumb_height - thumb.height) // 2
                canvas.paste(thumb, (offset_x, offset_y))
            draw.rectangle((x, y, x + thumb_width, y + thumb_height), outline='#9aa7b4', width=1)
            draw.text((x, y + thumb_height + 4), f'Page {page_number}', fill='#263747')

        sheet_path = sheets_dir / f'contact-{sheet_index + 1:03d}-{sheet_index + len(batch):03d}.jpg'
        canvas.save(sheet_path, quality=88, optimize=True)
        sheet_paths.append(sheet_path)

    return sheet_paths


def inspect_pdf(pdf_path: Path, rendered_pages: list[Path]) -> dict[str, object]:
    reader = PdfReader(pdf_path)
    page_text = [page.extract_text() or '' for page in reader.pages]
    combined_text = '\n'.join(page_text)
    media_boxes = {
        (
            round(float(page.mediabox.width), 2),
            round(float(page.mediabox.height), 2),
        )
        for page in reader.pages
    }
    blank_pages = []
    for index, text in enumerate(page_text, start=1):
        if index in (1, len(page_text)):
            continue
        cleaned = text
        cleaned = cleaned.replace(REPORT_VERSION, '')
        cleaned = cleaned.replace('大队长出品', '')
        cleaned = cleaned.replace('fqsx@mail.ustc.edu.cn', '')
        cleaned = re.sub(r'\b\d+\s*/\s*\d+\b', '', cleaned)
        lines = [
            re.sub(r'\s+', '', line)
            for line in cleaned.splitlines()
            if re.sub(r'\s+', '', line)
        ]
        if len(lines) <= 1 and sum(map(len, lines)) < 80:
            blank_pages.append(index)
    rendered_sizes = set()
    edge_touch_pages = []
    for image_path in rendered_pages:
        with Image.open(image_path) as image:
            rendered_sizes.add(image.size)
            grayscale = image.convert('L')
            width, height = grayscale.size
            edge_bands = (
                grayscale.crop((0, 0, 4, height)),
                grayscale.crop((width - 4, 0, width, height)),
                grayscale.crop((0, 0, width, 4)),
                grayscale.crop((0, height - 4, width, height)),
            )
            page_number = int(image_path.stem.split('-')[-1])
            if (
                page_number != 1
                and any(band.getextrema()[0] < 220 for band in edge_bands)
            ):
                edge_touch_pages.append(page_number)

    external_urls = []
    for page in reader.pages:
        for annotation_reference in page.get('/Annots', []):
            annotation = annotation_reference.get_object()
            action = annotation.get('/A')
            if action is None or action.get('/URI') is None:
                continue
            external_urls.append(str(action['/URI']))

    malformed_external_urls = sorted({
        url
        for url in external_urls
        if url.endswith(('%EF%BC%89', '）'))
    })

    def count_outline(items: list[object]) -> int:
        return sum(
            count_outline(item) if isinstance(item, list) else 1
            for item in items
        )

    return {
        'pdf': str(pdf_path),
        'pages': len(reader.pages),
        'rendered_pages': len(rendered_pages),
        'media_boxes_points': sorted(media_boxes),
        'rendered_image_sizes': sorted(rendered_sizes),
        'edge_touch_pages': sorted(edge_touch_pages),
        'text_characters': len(combined_text),
        'replacement_characters': combined_text.count('\ufffd'),
        'near_blank_pages': blank_pages,
        'figure_captions_found': len(set(re.findall(r'图\s+(?:\d+\.\d+|G\.\d+)', combined_text))),
        'bookmarks': count_outline(reader.outline),
        'external_links': len(external_urls),
        'unique_external_urls': len(set(external_urls)),
        'malformed_external_urls': malformed_external_urls,
        'contains_version': REPORT_VERSION in combined_text,
        'contains_appendix_g': '附录 G' in combined_text,
        'contains_appendix_h': '附录 H' in combined_text,
        'canonical_sections': sum(
            marker in combined_text
            for marker in ('卷一', '卷二', '卷三', '卷四', '卷五', '卷六', '卷七', '卷八', '卷九', '卷十')
        ),
    }


def main() -> int:
    args = parse_args()
    pdf_path = args.pdf.resolve()
    output_dir = args.output_dir.resolve()
    pages_dir = output_dir / 'pages'
    output_dir.mkdir(parents=True, exist_ok=True)

    page_images = render_pages(pdf_path, pages_dir, args.pdftoppm, args.dpi)
    contact_sheets = build_contact_sheets(page_images, output_dir)
    report = inspect_pdf(pdf_path, page_images)
    report['contact_sheets'] = [str(path) for path in contact_sheets]
    report_path = output_dir / 'qa-report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

    passed = (
        report['pages'] == report['rendered_pages']
        and report['replacement_characters'] == 0
        and report['near_blank_pages'] == []
        and report['edge_touch_pages'] == []
        and report['figure_captions_found'] == 13
        and report['bookmarks'] >= 300
        and report['malformed_external_urls'] == []
        and report['canonical_sections'] == 10
        and report['contains_version']
        and report['contains_appendix_g']
        and report['contains_appendix_h']
    )
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
