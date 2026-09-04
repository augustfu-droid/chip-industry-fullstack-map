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
URL_PATTERN = re.compile(r'https?://\S+')
PUBLIC_REPORT_END = '### 修改纪要 Changelog'
SECURITY_CODE_PATTERN = re.compile(
    r'(?<![A-Za-z0-9])'
    r'(?:000|001|002|003|159|300|301|430|'
    r'51[0-9]|56[0-9]|58[0-9]|'
    r'600|601|603|605|688|689|'
    r'83[0-9]|87[0-9]|88[0-9]|92[0-9])'
    r'\d{3}'
    r'(?!\d)'
)
STANDARD_NUMBER_PREFIX = re.compile(
    r'(?:GB(?:/T)?|ISO(?:/IEC)?|IEC|IEEE|JEDEC|SEMI|SAE)'
    r'\s*(?:No\.?\s*)?$',
    re.IGNORECASE,
)
PARENTHESIZED_US_TICKER = re.compile(
    r'[（(]\s*'
    r'(?P<ticker>[A-Z]{1,5}(?:\.[A-Z])?)'
    r'(?P<market>\s*,\s*US)?'
    r'\s*[）)]'
)
# Uppercase parenthetical tokens are often technical acronyms or ordinary
# corporate abbreviations. Restrict the denylist to stock symbols that differ
# from the issuer's common name, while always rejecting an explicit ", US"
# suffix, so terms such as (HBM), (AMD), (ASML) and (UMC) are not false hits.
US_TICKER_SYMBOLS = frozenset({
    'ALAB', 'AMAT', 'AVGO', 'CDNS', 'COHR', 'GFS', 'INTC', 'KLAC', 'LRCX',
    'MCHP', 'MRVL', 'MU', 'NVDA', 'NVTS', 'NXPI', 'QCOM', 'RMBS', 'SNPS',
    'TSM', 'WOLF',
})
PUBLIC_INVESTMENT_LANGUAGE = re.compile(
    r'核心受益|小仓位|核心仓位|主题性配置|确定性受益|'
    r'从\s*A\s*股投资角度|配置建议|建议配置|买入评级|增持评级'
)


class RepositoryIntegrityTests(unittest.TestCase):
    @staticmethod
    def _public_report_text():
        report_text = REPORT.read_text(encoding='utf-8')
        return report_text.partition(PUBLIC_REPORT_END)[0]

    @staticmethod
    def _format_matches(matches):
        return ', '.join(
            f'{"line " + str(line_number) if line_number else "document"}: '
            f'{value}'
            for line_number, value in matches
        )

    @staticmethod
    def _security_codes_in_text(text):
        matches = []
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            # DOI suffixes, dated URL paths and document IDs are not security
            # codes. Replacing URLs with equal-length whitespace preserves the
            # match offsets used for contextual checks and diagnostics.
            line = URL_PATTERN.sub(
                lambda match: ' ' * len(match.group(0)),
                raw_line,
            )
            for match in SECURITY_CODE_PATTERN.finditer(line):
                if STANDARD_NUMBER_PREFIX.search(line[:match.start()]):
                    continue
                matches.append((line_number, match.group(0)))
        return matches

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
        pdf_pages = int(pages_match.group(1))
        readme_pages_match = re.search(
            r'PDF 已随 Markdown 更新[^\n]+共\s*(\d+)\s*页',
            README.read_text(encoding='utf-8'),
        )
        self.assertIsNotNone(readme_pages_match)
        self.assertEqual(pdf_pages, int(readme_pages_match.group(1)))
        self.assertGreaterEqual(pdf_pages, 120)
        self.assertLessEqual(pdf_pages, 180)

        text = subprocess.run(
            ['pdftotext', str(VERSIONED_PDF), '-'],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertGreater(len(text), 250_000)
        self.assertNotIn('\ufffd', text)
        for required_text in (
            REPORT_VERSION,
            '第 39 章',
            '附录 G',
            '附录 H',
            '7,200–7,450 亿美元',
            '96.221 十亿美元',
            '16.7 十亿美元',
            '2.1715 十亿美元',
            '2.4768 十亿美元',
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

    def test_public_report_has_no_security_identifiers(self):
        public_text = self._public_report_text()
        identifiers = [
            (line_number, f'六位证券代码 {code}')
            for line_number, code in self._security_codes_in_text(public_text)
        ]
        for line_number, raw_line in enumerate(
            public_text.splitlines(),
            start=1,
        ):
            line = URL_PATTERN.sub(
                lambda match: ' ' * len(match.group(0)),
                raw_line,
            )
            for match in PARENTHESIZED_US_TICKER.finditer(line):
                ticker = match.group('ticker')
                if match.group('market') or ticker in US_TICKER_SYMBOLS:
                    identifiers.append(
                        (line_number, f'括号内美股 ticker {match.group(0)}')
                    )

        self.assertEqual(
            [],
            identifiers,
            '公开版含证券标识：' + self._format_matches(identifiers),
        )

    def test_security_code_filter_ignores_dates_standards_and_urls(self):
        non_security_numbers = (
            '维护月份 202605\n'
            '标准号 ISO 688981\n'
            '论文 https://doi.org/10.1109/JPROC.1998.658762\n'
        )
        self.assertEqual([], self._security_codes_in_text(non_security_numbers))
        self.assertEqual(
            [(1, '688981')],
            self._security_codes_in_text('证券代码 688981'),
        )

    def test_public_report_has_no_investment_action_language(self):
        matches = []
        for line_number, line in enumerate(
            self._public_report_text().splitlines(),
            start=1,
        ):
            matches.extend(
                (line_number, match.group(0))
                for match in PUBLIC_INVESTMENT_LANGUAGE.finditer(line)
            )
        self.assertEqual(
            [],
            matches,
            '公开版含操作或配置措辞：' + self._format_matches(matches),
        )

    def test_report_rejects_known_hard_errors_and_tracks_current_status(self):
        report_text = self._public_report_text()
        forbidden_patterns = {
            'CPO 旧功耗换算 2.6MW': r'2\.6\s*MW',
            'CPO 旧电量换算 2.3GWh': r'2\.3\s*GWh',
            '无一手依据的 Loihi 3': r'\bLoihi\s*3\b',
            '已取消路线的 18A Falcon Shores 量产': (
                r'\b18A\s+Falcon\s+Shores\s+量产'
            ),
        }
        problems = []
        for line_number, line in enumerate(report_text.splitlines(), start=1):
            for description, pattern in forbidden_patterns.items():
                if re.search(pattern, line):
                    problems.append((line_number, description))

        body_lines = [
            line
            for line in report_text.splitlines()
            if not re.match(r'^\[[^]]+\]\s', line)
        ]
        falcon_status = [
            line
            for line in body_lines
            if 'Falcon Shores' in line
            and re.search(r'取消|不再|终止|放弃', line)
            and re.search(r'商业化|商业产品', line)
        ]
        ironwood_status = [
            line
            for line in body_lines
            if 'Ironwood' in line
            and re.search(r'\bGA\b|全面可用|一般可用|正式商用', line)
        ]
        if not falcon_status:
            problems.append((
                0,
                '正文缺少 Falcon Shores 取消商业化/不再作为商业产品状态',
            ))
        if not ironwood_status:
            problems.append((
                0,
                '正文缺少 Ironwood 已 GA（一般可用）/正式商用状态',
            ))
        rubin_status = [
            line
            for line in body_lines
            if 'Rubin' in line
            and re.search(r'公司自报量产|全量生产', line)
            and re.search(r'机架运行|合作伙伴', line)
        ]
        if not rubin_status:
            problems.append((
                0,
                '正文缺少 Rubin 公司自报量产与合作伙伴机架运行状态',
            ))
        groq_status = [
            line
            for line in body_lines
            if 'Groq 3 LPX' in line
            and re.search(r'全量生产', line)
            and re.search(r'采用|可用', line)
        ]
        if not groq_status:
            problems.append((
                0,
                '正文缺少 Groq 3 LPX 全量生产与采用边界',
            ))
        self.assertEqual(
            [],
            problems,
            '公开版含已知硬错误或缺少当前状态：'
            + self._format_matches(problems),
        )

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

    def test_financial_appendix_tracks_latest_capex_guidance(self):
        report_text = REPORT.read_text(encoding='utf-8')
        appendix = report_text[
            report_text.index('### 附录 G'):
            report_text.index('### 附录 H')
        ]
        for required_text in (
            '约 175 十亿美元',
            '195–205 十亿美元',
            '130–145 十亿美元',
            '约 220 十亿美元',
            '7,200–7,450 亿美元',
            '175+195+130+220=720',
            '175+205+145+220=745',
            '租赁会计分类变化',
        ):
            self.assertIn(required_text, appendix)
        for stale_text in (
            '7,150–7,400 亿美元',
            '7,350–7,600 亿美元',
            '190+195+130+200=715',
            '190+205+145+200=740',
        ):
            self.assertNotIn(stale_text, appendix)

    def test_financial_appendix_tracks_nvidia_q2_fy2027(self):
        report_text = REPORT.read_text(encoding='utf-8')
        appendix = report_text[
            report_text.index('### 附录 G'):
            report_text.index('### 附录 H')
        ]
        for required_text in (
            '96.221 十亿美元',
            '89.0 十亿美元',
            '24.077 十亿美元',
            '21.341 十亿美元',
            '108.0 十亿美元 ±2%',
            '应收与存货分别消耗 22.346 与 5.784 十亿美元经营现金',
        ):
            self.assertIn(required_text, appendix)

    def test_v113_disclosures_preserve_metric_boundaries(self):
        report_text = self._public_report_text()
        appendix = report_text[
            report_text.index('### 附录 G'):
            report_text.index('### 附录 H')
        ]
        for required_text in (
            'AI 半导体指标覆盖定制加速器与网络',
            '不能与半导体解决方案收入重复相加',
            '数据中心口径还含以太网、服务器、存储与 DCI',
            '认股权证归属条件不是已承诺订单或已确认收入',
            'Design Automation 也包含 Ansys',
            '不能当作纯 EDA 有机增速',
        ):
            self.assertIn(required_text, appendix)


if __name__ == '__main__':
    unittest.main()
