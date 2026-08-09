import ast
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / 'README.md'
REPORT = ROOT / '芯片产业链全栈技术图谱_公开版.md'
VERSION_MATCH = re.search(
    r'^>\s*版本\s+([^·\s]+)',
    REPORT.read_text(encoding='utf-8'),
    re.MULTILINE,
)
if VERSION_MATCH is None:
    raise RuntimeError(f'无法从报告元数据读取版本号：{REPORT}')
REPORT_VERSION = VERSION_MATCH.group(1)
FIGURES = ROOT / 'figures'
FIGURE_NOTES = FIGURES / 'README.md'
GENERATOR = ROOT / 'gen_figures.py'
PDF_BUILDER = ROOT / 'build_pdf.mjs'
PDF_STYLESHEET = ROOT / 'pdf' / 'report.css'
PDF_QA = ROOT / 'scripts' / 'qa_pdf.py'
VERSIONED_PDF = (
    ROOT
    / 'output'
    / 'pdf'
    / f'芯片产业链全栈技术图谱_公开版_{REPORT_VERSION}.pdf'
)
CANONICAL_PDF = ROOT / '芯片产业链全栈技术图谱_公开版.pdf'
MARKDOWN_FILES = (README, REPORT, FIGURE_NOTES)
LINK_PATTERN = re.compile(r'!?\[[^\]]*\]\(([^)]+)\)')
IMAGE_PATTERN = re.compile(r'!\[[^\]]+\]\(([^)]+)\)')
HEADING_PATTERN = re.compile(r'^(#{1,6})\s+\S')


class RepositoryIntegrityTests(unittest.TestCase):
    def test_python_source_parses(self):
        ast.parse(GENERATOR.read_text(encoding='utf-8'))
        ast.parse(PDF_QA.read_text(encoding='utf-8'))

    def test_pdf_build_inputs_exist(self):
        for path in (PDF_BUILDER, PDF_STYLESHEET, PDF_QA):
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 0, path)

        builder_text = PDF_BUILDER.read_text(encoding='utf-8')
        for required_text in ('marked', 'weasyprint', '--pdf-tags', '--base-url'):
            self.assertIn(required_text, builder_text)

    def test_current_pdf_artifacts_are_complete_and_identical(self):
        self.assertTrue(VERSIONED_PDF.is_file())
        self.assertTrue(CANONICAL_PDF.is_file())
        versioned_bytes = VERSIONED_PDF.read_bytes()
        self.assertEqual(b'%PDF-', versioned_bytes[:5])
        self.assertEqual(versioned_bytes, CANONICAL_PDF.read_bytes())

        pdf_info = subprocess.run(
            ['pdfinfo', str(VERSIONED_PDF)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertIn('Title:           芯片产业链全栈技术图谱与演进架构', pdf_info)
        self.assertIn('Tagged:          yes', pdf_info)
        pages_match = re.search(r'^Pages:\s+(\d+)$', pdf_info, re.MULTILINE)
        self.assertIsNotNone(pages_match)
        self.assertGreaterEqual(int(pages_match.group(1)), 140)

        text = subprocess.run(
            ['pdftotext', str(VERSIONED_PDF), '-'],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertNotIn('\ufffd', text)
        for required_text in (
            REPORT_VERSION,
            '第 39 章',
            '附录 G',
            '附录 H',
            '修改纪要 Changelog',
        ):
            self.assertIn(required_text, text)
        figure_numbers = set(
            re.findall(r'图\s+(?:\d+\.\d+|G\.\d+)', text)
        )
        self.assertEqual(13, len(figure_numbers))

    def test_generator_smoke_builds_all_figures(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / 'matplotlib'
            output_dir = Path(temp_dir) / 'figures'
            env = os.environ.copy()
            env['MPLCONFIGDIR'] = str(config_dir)
            list_result = subprocess.run(
                [sys.executable, '-B', str(GENERATOR), '--list'],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    '-B',
                    str(GENERATOR),
                    '--output-dir',
                    str(output_dir),
                    '--dpi',
                    '72',
                ],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            figure_names = [
                line
                for line in list_result.stdout.splitlines()
                if line
            ]
            generated = sorted(output_dir.glob('*.png'))
            self.assertEqual(13, len(figure_names))
            self.assertEqual(len(figure_names), len(set(figure_names)))
            self.assertEqual(13, len(generated))
            for image_path in generated:
                data = image_path.read_bytes()
                self.assertEqual(b'\x89PNG\r\n\x1a\n', data[:8])
                width, height = struct.unpack('>II', data[16:24])
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)

    def test_local_markdown_targets_exist(self):
        missing = []
        for markdown_file in MARKDOWN_FILES:
            text = markdown_file.read_text(encoding='utf-8')
            for raw_target in LINK_PATTERN.findall(text):
                target = unquote(raw_target.split('#', 1)[0])
                if not target or target.startswith(('http://', 'https://', 'mailto:')):
                    continue
                resolved = (markdown_file.parent / target).resolve()
                if not resolved.exists():
                    missing.append(f'{markdown_file.name}: {raw_target}')
        self.assertEqual([], missing)

    def test_every_png_is_embedded_in_report(self):
        report_text = REPORT.read_text(encoding='utf-8')
        embedded = {
            Path(target).name
            for target in IMAGE_PATTERN.findall(report_text)
            if not target.startswith(('http://', 'https://'))
        }
        published = {path.name for path in FIGURES.glob('*.png')}
        self.assertSetEqual(published, embedded)

    def test_images_have_nonempty_alt_text(self):
        for markdown_file in MARKDOWN_FILES:
            text = markdown_file.read_text(encoding='utf-8')
            empty_alt = re.findall(r'!\[\s*\]\([^)]+\)', text)
            self.assertEqual([], empty_alt, markdown_file.name)

    def test_heading_levels_do_not_skip(self):
        for markdown_file in MARKDOWN_FILES:
            previous_level = None
            errors = []
            for line_number, line in enumerate(
                markdown_file.read_text(encoding='utf-8').splitlines(),
                start=1,
            ):
                match = HEADING_PATTERN.match(line)
                if not match:
                    continue
                level = len(match.group(1))
                if previous_level is not None and level > previous_level + 1:
                    errors.append((line_number, previous_level, level))
                previous_level = level
            self.assertEqual([], errors, markdown_file.name)

    def test_report_heading_text_is_unique(self):
        headings = []
        for line in REPORT.read_text(encoding='utf-8').splitlines():
            if HEADING_PATTERN.match(line):
                headings.append(line.lstrip('#').strip())
        duplicates = sorted({
            heading
            for heading in headings
            if headings.count(heading) > 1
        })
        self.assertEqual([], duplicates)

    def test_chapters_20_to_29_use_chapter_scoped_citations(self):
        chapter = None
        plain_citations = []
        definitions = {number: set() for number in range(20, 30)}
        uses = {number: set() for number in range(20, 30)}
        for line_number, line in enumerate(
            REPORT.read_text(encoding='utf-8').splitlines(),
            start=1,
        ):
            chapter_match = re.match(r'^### 第 (\d+) 章', line)
            if chapter_match:
                chapter = int(chapter_match.group(1))
            if chapter not in definitions:
                continue
            if re.search(r'\[\d+(?:\s*,\s*\d+)*\]', line):
                plain_citations.append(line_number)
            uses[chapter].update(
                re.findall(rf'(?<!\d){chapter}-(\d+)(?!\d)', line)
            )
            definition = re.match(rf'^\[{chapter}-(\d+)\]\s', line)
            if definition:
                definitions[chapter].add(definition.group(1))

        self.assertEqual([], plain_citations)
        for chapter in definitions:
            self.assertSetEqual(uses[chapter], definitions[chapter])

    def test_report_has_no_placeholder_figure_numbers(self):
        report_text = REPORT.read_text(encoding='utf-8')
        self.assertNotRegex(report_text, r'图\s+[0-9A-Z]+\.[xX]\b')

    def test_bare_urls_do_not_absorb_chinese_parentheses(self):
        report_text = REPORT.read_text(encoding='utf-8')
        self.assertNotRegex(report_text, r'（https?://[^）]+）')

    def test_financial_appendix_uses_auditable_scope(self):
        report_text = REPORT.read_text(encoding='utf-8')
        self.assertNotIn('2025E 合计 Capex 约 3,500 亿美元', report_text)
        self.assertNotIn('2026E 约 4,200 亿美元', report_text)
        for required_text in (
            '事实—假设—判断（F/A/J）',
            '三张表勾稽',
            '可复用的子赛道研究卡',
            '不应标注为「五大云厂商 AI Capex」',
        ):
            self.assertIn(required_text, report_text)

        appendix = report_text[
            report_text.index('### 附录 G'):
            report_text.index('### 附录 H')
        ]
        uses = set(re.findall(r'\[G-(\d+)\]', appendix))
        definitions = set(re.findall(r'^\[G-(\d+)\]\s', appendix, re.MULTILINE))
        self.assertSetEqual(uses, definitions)


if __name__ == '__main__':
    unittest.main()
