"""批量生成芯片产业链报告插图。

- 统一配色（与 PDF 设计语言对齐）
- 自动选择可用中文字体
- 默认输出到仓库内的 ``figures/``，支持命令行覆盖目录和 DPI
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
import matplotlib.font_manager as fm
from matplotlib.ft2font import FT2Font
from matplotlib.colors import to_rgb
from matplotlib.text import Text
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_OUT_DIR = PROJECT_DIR / 'figures'
DEFAULT_DPI = 200
OUT_DIR = DEFAULT_OUT_DIR
OUTPUT_DPI = DEFAULT_DPI
SELECTED_FONT_CHARMAP = set()
SELECTED_FONT_NAME = None

# ---- 中文字体 ----
# 优先使用仓库内字体；兼容原构建环境和常见 Linux 字体目录。
FONT_FILES = (
    PROJECT_DIR / 'fonts/NotoSansSC-Regular.ttf',
    PROJECT_DIR / 'fonts/NotoSansSC-Bold.ttf',
    Path('/home/user/workspace/fonts/NotoSansSC-Regular.ttf'),
    Path('/home/user/workspace/fonts/NotoSansSC-Bold.ttf'),
    Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
    Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'),
)

CJK_FONT_CANDIDATES = (
    'Noto Sans SC',
    'Noto Sans CJK SC',
    'Noto Sans CJK JP',
    'Source Han Sans SC',
    'Microsoft YaHei',
    'PingFang SC',
    'Arial Unicode MS',
    'PingFang HK',
    'WenQuanYi Zen Hei',
)


def _configure_cjk_font():
    """选择真正覆盖常用中文字符的字体，避免静默生成方框字。"""
    global SELECTED_FONT_CHARMAP, SELECTED_FONT_NAME

    load_errors = []
    for font_path in FONT_FILES:
        if font_path.exists():
            try:
                fm.fontManager.addfont(font_path)
            except Exception as exc:
                load_errors.append(f'{font_path}: {exc}')

    available = {font.name for font in fm.fontManager.ttflist}
    probe = set('芯片产业链图表')
    for candidate in CJK_FONT_CANDIDATES:
        if candidate not in available:
            continue
        try:
            font_file = fm.findfont(candidate, fallback_to_default=False)
            charmap = FT2Font(font_file).get_charmap()
        except Exception as exc:
            load_errors.append(f'{candidate}: {exc}')
            continue
        if all(ord(char) in charmap for char in probe):
            plt.rcParams['font.family'] = [candidate]
            plt.rcParams['axes.unicode_minus'] = False
            SELECTED_FONT_NAME = candidate
            SELECTED_FONT_CHARMAP = set(charmap)
            print(f'using font: {candidate}')
            return

    details = f"\n字体加载错误：{'; '.join(load_errors)}" if load_errors else ''
    raise RuntimeError(
        '未找到覆盖中文字符的字体。请安装 Noto Sans CJK SC / 思源黑体后重试。'
        f'{details}'
    )

# ---- 调色板 (财经/科技调) ----
TEAL = '#01696F'
TEAL_LIGHT = '#5BA8AC'
GOLD = '#7A5A00'
GOLD_LIGHT = '#E8C76A'
BROWN = '#6E522B'
BG = '#F7F6F2'
TEXT = '#2A2A2A'
MUTED = '#6A6A6A'
RED = '#B73E3E'
BLUE = '#2E5C8A'
GREEN = '#3F7A4A'
PURPLE = '#7A4A7A'

def _relative_luminance(color):
    channels = []
    for channel in to_rgb(color):
        channels.append(
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(foreground, background):
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _readable_text_color(background):
    """在深色正文和白色之间选择对比度更高者。"""
    candidates = (TEXT, '#FFFFFF')
    selected = max(candidates, key=lambda color: _contrast_ratio(color, background))
    ratio = _contrast_ratio(selected, background)
    if ratio < 4.5:
        raise ValueError(f'标签配色对比度不足：{selected} / {background} = {ratio:.2f}:1')
    return selected


def _style(ax, title=None, xlabel=None, ylabel=None, grid_axis='y'):
    ax.set_facecolor(BG)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color('#999999')
        ax.spines[spine].set_linewidth(0.8)
    ax.tick_params(colors=TEXT, labelsize=9)
    if grid_axis:
        ax.grid(axis=grid_axis, color='#D8D8D8', linestyle='--', linewidth=0.6, alpha=0.7)
        ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=13, color=TEXT, fontweight='bold', pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, color=TEXT)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, color=TEXT)


def _save(fig, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f'{name}.png'
    fig.patch.set_facecolor(BG)
    missing_glyphs = {
        char
        for text_object in fig.findobj(match=Text)
        for char in text_object.get_text()
        if ord(char) > 127
        and not char.isspace()
        and ord(char) not in SELECTED_FONT_CHARMAP
    }
    if missing_glyphs:
        missing = ''.join(sorted(missing_glyphs))
        raise RuntimeError(f'字体 {SELECTED_FONT_NAME} 缺少图中字符：{missing}')
    fig.savefig(path, dpi=OUTPUT_DPI, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print('  ✓', path)
    return path


# ============================================================
# 图 1: 国产化进度雷达图 (1.5 节承诺的图)
# ============================================================
def fig_localization_radar():
    categories = ['设计\n(数字 SoC)', '设计\n(模拟/射频)', 'EDA\n工具', '制造\n(成熟制程)', '制造\n(先进制程)',
                  '设备\n(刻蚀/沉积)', '设备\n(光刻)', '材料\n(基础)', '材料\n(高端)', '封测']
    cn_values = [72, 45, 12, 65, 8, 40, 3, 55, 18, 80]
    intl_values = [95, 90, 95, 98, 95, 92, 95, 90, 85, 90]

    angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
    cn_values_p = cn_values + [cn_values[0]]
    intl_values_p = intl_values + [intl_values[0]]
    angles_p = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(9, 8), subplot_kw=dict(polar=True))
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    ax.plot(angles_p, intl_values_p, color=BROWN, linewidth=1.5, linestyle='--', label='国际领先水平 (基准)')
    ax.fill(angles_p, intl_values_p, color=BROWN, alpha=0.06)

    ax.plot(angles_p, cn_values_p, color=TEAL, linewidth=2.2, label='中国大陆国产化率 (%)')
    ax.fill(angles_p, cn_values_p, color=TEAL, alpha=0.25)

    ax.set_xticks(angles)
    ax.set_xticklabels(categories, fontsize=10, color=TEXT)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=8, color=MUTED)
    ax.set_rlabel_position(90)
    ax.grid(color='#CCCCCC', linewidth=0.6, alpha=0.7)

    for ang, v, lab in zip(angles, cn_values, categories):
        ax.text(ang, v + 6, f'{v}%', ha='center', va='center', fontsize=8.5,
                color=TEAL, fontweight='bold')

    ax.set_title('图 1.5  中国大陆半导体产业链各环节国产化率雷达图\n(数据综合 SIA / IC Insights / SEMI / 各券商研报口径, 2024-2025)',
                 fontsize=12, color=TEXT, pad=22, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), fontsize=9, frameon=False)
    return _save(fig, 'fig_1_5_localization_radar')


# ============================================================
# 图 2: 产业链全景图 (卷一)
# ============================================================
def fig_industry_overview():
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8.5)
    ax.axis('off')
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    ax.text(7, 8.0, '芯片产业链十卷全景', ha='center', fontsize=16, fontweight='bold', color=TEXT)
    ax.text(7, 7.5, '上游 → 中游 → 下游 · 设计 / 制造 / 封测 / 应用', ha='center', fontsize=10, color=MUTED)

    sections = [
        ('上游基石', [('设计 IP\n& EDA', '卷二'), ('物理 & 材料\n突破', '卷三')], TEAL, 0.5, 6.0),
        ('中游制造', [('前道工艺\n(FEOL)', '卷四'), ('中道 & 封装\n(BEOL)', '卷五')], GOLD, 4.0, 6.0),
        ('下游算力', [('互连 & 存储\n(HBM/CXL)', '卷六'), ('异构计算\n(CPU/GPU/NPU)', '卷七')], BROWN, 7.5, 6.0),
        ('生态支撑', [('软件栈 &\n软硬协同', '卷八'), ('应用 & 终端\n市场', '卷九')], BLUE, 11.0, 6.0),
    ]

    for title, items, color, x0, y0 in sections:
        ax.add_patch(FancyBboxPatch((x0, y0-0.1), 2.5, 0.6, boxstyle='round,pad=0.04',
                                      facecolor=color, edgecolor='none'))
        ax.text(
            x0 + 1.25,
            y0 + 0.2,
            title,
            ha='center',
            va='center',
            fontsize=11,
            color=_readable_text_color(color),
            fontweight='bold',
        )
        for i, (name, vol) in enumerate(items):
            yy = y0 - 0.9 - i*1.5
            ax.add_patch(FancyBboxPatch((x0, yy-0.55), 2.5, 1.1, boxstyle='round,pad=0.04',
                                          facecolor='white', edgecolor=color, linewidth=1.5))
            ax.text(x0+1.25, yy+0.15, name, ha='center', va='center', fontsize=10, color=TEXT, fontweight='bold')
            ax.text(x0+1.25, yy-0.32, vol, ha='center', va='center', fontsize=8.5, color=color, fontweight='bold')

    # 底部地缘政治带
    ax.add_patch(FancyBboxPatch((0.5, 0.3), 13.0, 0.7, boxstyle='round,pad=0.05',
                                  facecolor=RED, edgecolor='none'))
    ax.text(7, 0.65, '卷十 · 地缘政治 / 产业政策 / 产业研究框架  ——  贯穿全链的宏观变量', ha='center', va='center',
            fontsize=11, color=_readable_text_color(RED), fontweight='bold')

    # 上下游箭头
    for x in (3.0, 6.5, 10.0):
        ax.annotate('', xy=(x+1.05, 6.3), xytext=(x, 6.3),
                    arrowprops=dict(arrowstyle='->', color=MUTED, lw=1.5))

    return _save(fig, 'fig_v1_industry_overview')


# ============================================================
# 图 3: 制程演进时间线 (卷三)
# ============================================================
def fig_node_roadmap():
    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(2019, 2031)
    ax.set_ylim(0, 6)
    ax.axis('off')

    # 主时间轴
    ax.add_patch(Rectangle((2019, 2.8), 12, 0.12, color=TEAL, alpha=0.5))

    milestones = [
        (2020, '[F] N5\nFinFET', 'TSMC', TEAL, 'top', 2020.0),
        (2022, '[F] N3 / SF3\nFinFET / GAA', 'TSMC / Samsung', GOLD, 'bottom', 2022.0),
        (2025, '[F] N2 HVM\nGAA Nanosheet', 'TSMC', GOLD, 'top', 2025.0),
        (2025, '[F] 18A\n进入生产', 'Intel', BROWN, 'bottom', 2024.7),
        (2026, '[T] N2P / A16\n公司目标', 'TSMC', GOLD, 'top', 2026.35),
        (2028, '[T] A14\n公司目标', 'TSMC', GOLD, 'bottom', 2028.0),
        (2030, '[A] CFET\n研究窗口', '行业研究', RED, 'top', 2030.0),
    ]

    box_width = 1.15
    box_height = 1.15
    for year, label, vendor, color, side, label_x in milestones:
        y_label = 4.5 if side == 'top' else 1.25
        y_marker = 3.0 if side == 'top' else 2.7
        box_edge_y = y_label - box_height / 2 if side == 'top' else y_label + box_height / 2
        ax.plot([year, label_x], [y_marker, box_edge_y],
                color=color, linewidth=1.0, alpha=0.6)
        ax.add_patch(Circle((year, 2.86), 0.13, color=color, zorder=5))
        ax.add_patch(FancyBboxPatch((label_x - box_width / 2, y_label - box_height / 2),
                                      box_width, box_height, boxstyle='round,pad=0.02',
                                      facecolor='white', edgecolor=color, linewidth=1.3))
        ax.text(label_x, y_label + 0.16, label, ha='center', va='center', fontsize=7.6,
                color=TEXT, fontweight='bold', linespacing=1.05)
        ax.text(label_x, y_label - 0.38, vendor, ha='center', va='center', fontsize=7, color=color)

    for y in range(2019, 2032, 2):
        ax.text(y, 2.4, str(y), ha='center', va='top', fontsize=9, color=MUTED, fontweight='bold')

    ax.text(2025, 5.5, '图 10.1  全球先进制程证据状态时间线（F 已发生 / T 公司目标 / A 研究假设）',
            ha='center', fontsize=13, color=TEXT, fontweight='bold')

    # Legend
    legend_items = [
        ('FinFET 阶段', TEAL),
        ('GAA Nanosheet', GOLD),
        ('BSPDN / RibbonFET', BROWN),
        ('CFET 三维堆叠', RED),
    ]
    for i, (name, color) in enumerate(legend_items):
        ax.add_patch(Circle((2019.5 + i*2.5, 0.3), 0.1, color=color))
        ax.text(2019.7 + i*2.5, 0.3, name, va='center', fontsize=9, color=TEXT)

    return _save(fig, 'fig_v3_node_roadmap')


# ============================================================
# 图 4: EUV / High-NA 光刻路线 (卷四)
# ============================================================
def fig_litho_roadmap():
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(BG)
    _style(ax, title='图 9.1  EUV / High-NA 平台状态（设备事实与客户目标分开）',
           xlabel='年份', ylabel='数值孔径 NA')

    # 各系列独立建模，避免把 High-NA 首点错误连接到 NA=0.33 路线。
    nxe_years = [2019, 2023, 2026]
    nxe_na = [0.33, 0.33, 0.33]
    high_na_years = [2023, 2026, 2027.5]
    high_na_na = [0.55, 0.55, 0.55]

    ax.plot(nxe_years, nxe_na, 'o-', color=TEAL, linewidth=2.5, markersize=9,
            label='NXE:3400/3600 系列 (NA=0.33)')
    ax.plot(high_na_years, high_na_na, 's-', color=GOLD, linewidth=2.5, markersize=9,
            label='EXE:5000 系列 (High-NA, NA=0.55)')

    annotations = [
        (2019, 0.33, '[F] EUV 量产导入'),
        (2023, 0.55, '[F] 首套 High-NA 系统'),
        (2026, 0.55, '[T] 年末满足 HVM 要求'),
        (2027.5, 0.55, '[T] 2027–2028\n客户插入窗口'),
    ]
    for x, y, t in annotations:
        offset = 0.055 if y > 0.4 else -0.055
        ax.annotate(t, xy=(x, y), xytext=(x, y + offset), fontsize=8, ha='center', color=TEXT,
                    arrowprops=dict(arrowstyle='->', color=MUTED, lw=0.7))

    ax.legend(loc='center right', fontsize=9, frameon=False)
    ax.set_xlim(2018, 2029)
    ax.set_ylim(0.22, 0.66)
    return _save(fig, 'fig_v4_litho_roadmap')


# ============================================================
# 图 5: 先进封装家族象限图 (卷五)
# ============================================================
def fig_packaging_quadrant():
    fig, ax = plt.subplots(figsize=(11, 8))
    fig.patch.set_facecolor(BG)
    _style(ax, title='图 17.1  先进封装家族: 互连密度 vs 集成层次',
           xlabel='互连密度 (I/O per mm² , log)', ylabel='集成层次 ▶  (2D → 2.5D → 3D)',
           grid_axis='both')

    techs = [
        ('Wire Bond',       80,    1, 200, '#8C8C8C', 'Wire'),
        ('Flip Chip BGA',   400,   1.4, 280, BLUE, 'FCBGA'),
        ('Fan-Out WLP',     2000,  1.8, 350, TEAL_LIGHT, 'FO-WLP'),
        ('CoWoS-S\n(2.5D Si Interposer)', 8000, 2.5, 700, TEAL, 'CoWoS-S'),
        ('CoWoS-L\n(LSI Bridge)',         12000,2.7, 700, TEAL, 'CoWoS-L'),
        ('Foveros\n(3D Active)',          15000,3.4, 580, BROWN, 'Foveros'),
        ('SoIC / Hybrid Bond',            60000,3.8, 700, GOLD, 'SoIC'),
        ('Foveros Direct',                100000,4.0, 600, RED, 'Foveros-Direct'),
    ]

    for name, x, y, s, color, _ in techs:
        ax.scatter(x, y, s=s, color=color, alpha=0.7, edgecolor='white', linewidth=2, zorder=3)
        ax.text(x, y + 0.2, name, ha='center', va='bottom', fontsize=8.5, color=TEXT, fontweight='bold')

    ax.set_xscale('log')
    ax.set_xlim(50, 200000)
    ax.set_ylim(0.5, 4.7)

    # 阶段背景
    ax.axhspan(0.5, 1.7, color='#E8E8E8', alpha=0.3, label='2D 平面互连')
    ax.axhspan(1.7, 3.0, color='#FFE9C0', alpha=0.3, label='2.5D 中介层')
    ax.axhspan(3.0, 4.7, color='#FFD0C0', alpha=0.3, label='3D 堆叠')
    ax.legend(loc='lower right', fontsize=9, frameon=False)
    return _save(fig, 'fig_v5_packaging_quadrant')


# ============================================================
# 图 6: HBM 演进堆叠 (卷六)
# ============================================================
def fig_hbm_evolution():
    fig, ax = plt.subplots(figsize=(12, 6.5))
    fig.patch.set_facecolor(BG)
    _style(ax, title='图 20.1  HBM 高带宽内存代际演进 (容量 / 带宽 / 堆叠层数)',
           xlabel='', ylabel='单 Stack 带宽 (GB/s)')

    gens = ['HBM2', 'HBM2E', 'HBM3', 'HBM3E', 'HBM4', 'HBM4E 样品']
    bw = [256, 460, 819, 1200, 2800, 3600]
    cap = [8, 16, 24, 24, 36, 48]   # representative disclosed product, GB per stack
    layers = [8, 8, 12, 8, 12, 12]
    years = [2018, 2020, 2022, 2024, 2026, 2026]

    x = np.arange(len(gens))
    bars = ax.bar(x - 0.2, bw, 0.4, color=TEAL, alpha=0.85, label='带宽 GB/s (左轴)')
    for bar, v in zip(bars, bw):
        ax.text(bar.get_x() + bar.get_width()/2, v + 80, f'{v}', ha='center', fontsize=8.5, color=TEAL, fontweight='bold')

    ax2 = ax.twinx()
    ax2.plot(x + 0.2, cap, 'o-', color=GOLD, linewidth=2.5, markersize=10, label='容量 GB/stack (右轴)')
    for xi, c in zip(x, cap):
        ax2.text(xi + 0.2, c + 4, f'{c}GB', ha='center', fontsize=8.5, color=GOLD, fontweight='bold')

    ax2.spines['top'].set_visible(False)
    ax2.set_ylabel('单 Stack 容量 (GB)', color=GOLD, fontsize=10)
    ax2.tick_params(axis='y', colors=GOLD)
    ax2.set_ylim(0, 60)

    ax.set_xticks(x)
    ax.set_xticklabels([f'{g}\n({y}年 · {l} 层)' for g, y, l in zip(gens, years, layers)], fontsize=9.5, color=TEXT)
    ax.set_ylim(0, 4100)
    ax.legend(loc='upper left', fontsize=9, frameon=False)
    ax2.legend(loc='upper left', bbox_to_anchor=(0, 0.92), fontsize=9, frameon=False)
    return _save(fig, 'fig_v6_hbm_evolution')


# ============================================================
# 图 7: AI 芯片格局气泡图 (卷七)
# ============================================================
def fig_ai_chip_bubble():
    fig, ax = plt.subplots(figsize=(12, 7.5))
    fig.patch.set_facecolor(BG)
    _style(
        ax,
        title='图 22.1  AI 训练芯片格局: 算力 vs 高速存储 vs 价格量级 (2024-2025)',
        xlabel='单卡 BF16 算力 (PFLOPS)',
        ylabel='高速存储容量 (GB；HBM / 片上 SRAM)',
        grid_axis='both',
    )

    # (name, BF16 PFLOPS, HBM GB, price kUSD, color)
    chips = [
        ('NVIDIA H100',     1.0,   80,  30, TEAL),
        ('NVIDIA H200',     1.0,   141, 35, TEAL),
        ('NVIDIA B200',     2.3,   192, 45, TEAL),
        ('NVIDIA GB200',    5.0,   384, 70, TEAL),
        ('AMD MI300X',      1.3,   192, 25, BLUE),
        ('AMD MI325X',      1.3,   256, 30, BLUE),
        ('AMD MI350X',      2.6,   288, 40, BLUE),
        ('Intel Gaudi 3',   1.835, 128, 25, BROWN),
        ('Google TPU v5p',  0.918, 95,  20, GOLD),
        ('Google TPU v6e',  1.8,   96,  18, GOLD),
        ('AWS Trainium2',   1.3,   96,  18, PURPLE),
        ('Cerebras WSE-3',  0.125, 44,  3000, RED),  # 单晶圆级，价格特殊
        ('华为昇腾 910B',     0.376, 64,  15, GREEN),
    ]

    label_offsets = {
        'NVIDIA H100': (10, -18),
        'NVIDIA H200': (-10, 8),
        'AMD MI300X': (12, -13),
        'AMD MI325X': (12, 9),
        'Intel Gaudi 3': (12, 8),
        'Google TPU v5p': (-28, 14),
        'Google TPU v6e': (12, 10),
        'AWS Trainium2': (20, -14),
        'Cerebras WSE-3': (25, -18),
        '华为昇腾 910B': (-5, 18),
    }
    for name, flops, hbm, price, color in chips:
        # 价格跨度从单卡到系统级，使用对数面积映射，避免截断后仍声称成比例。
        size = (np.log10(price) + 0.5) * 360
        ax.scatter(flops, hbm, s=size, color=color, alpha=0.65, edgecolor='white', linewidth=1.5)
        dx, dy = label_offsets.get(name, (0, 8))
        ax.annotate(
            name,
            (flops, hbm),
            xytext=(dx, dy),
            textcoords='offset points',
            ha='center',
            fontsize=8,
            color=TEXT,
            fontweight='bold',
        )

    ax.set_xlim(-0.2, 5.5)
    ax.set_ylim(0, 420)

    # 使用代理对象生成图例，不在数据坐标中绘制“假数据点”。
    vendors = [('NVIDIA', TEAL), ('AMD', BLUE), ('Intel', BROWN), ('Google', GOLD),
               ('AWS', PURPLE), ('Cerebras', RED), ('华为', GREEN)]
    handles = [
        plt.Line2D(
            [0],
            [0],
            marker='o',
            linestyle='none',
            markerfacecolor=color,
            markeredgecolor='white',
            markersize=9,
            label=name,
        )
        for name, color in vendors
    ]
    ax.legend(handles=handles, loc='upper left', ncol=2, fontsize=8.5, frameon=False)
    ax.text(
        5.35,
        405,
        '气泡面积按价格量级对数映射；Cerebras 为系统级，不与单卡价格直接可比',
        fontsize=8.2,
        color=MUTED,
        style='italic',
        ha='right',
    )

    return _save(fig, 'fig_v7_ai_chip_bubble')


# ============================================================
# 图 8: 各 CSP 自研 ASIC 路线甘特图 (卷七)
# ============================================================
def fig_csp_asic_gantt():
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    ax.tick_params(colors=TEXT)

    rows = [
        ('Google TPU',  [('TPU v4', 2021, 2023, GOLD_LIGHT),
                          ('TPU v5p', 2023, 2025, GOLD),
                          ('TPU v6 Trillium', 2024, 2026, GOLD),
                          ('TPU v7', 2026, 2028, BROWN)]),
        ('AWS Inferentia (推理)', [('Inferentia 2', 2022, 2025, '#A8C5DC'),
                                        ('Inferentia 3 (规划)', 2025, 2027, '#7AA2C5')]),
        ('AWS Trainium (训练)', [('Trainium 1', 2022, 2024, '#8AB0D8'),
                                      ('Trainium 2', 2024, 2026, BLUE),
                                      ('Trainium 3 (规划)', 2026, 2028, BROWN)]),
        ('Meta MTIA',   [('MTIA v1', 2023, 2024, '#C8A8C8'),
                          ('MTIA v2', 2024, 2026, PURPLE),
                          ('MTIA v3 训练', 2026, 2028, BROWN)]),
        ('Microsoft Maia', [('Maia 100', 2023, 2025, TEAL_LIGHT),
                             ('Maia 200', 2025, 2027, TEAL),
                             ('Maia 300', 2027, 2029, BROWN)]),
        ('OpenAI', [('与 Broadcom 合研', 2025, 2027, '#D0A0A0'),
                     ('首颗 ASIC 量产', 2027, 2029, RED)]),
        ('华为 昇腾', [('910B', 2023, 2025, '#A0C5A0'),
                       ('910C', 2025, 2026, GREEN),
                       ('920 (规划)', 2026, 2028, BROWN)]),
    ]

    y_labels = []
    for i, (company, items) in enumerate(rows):
        y_labels.append(company)
        for name, s, e, color in items:
            ax.barh(i, e - s, left=s, color=color, edgecolor='white', linewidth=1.5, height=0.6)
            ax.text(
                (s + e) / 2,
                i,
                name,
                ha='center',
                va='center',
                fontsize=8.5,
                color=_readable_text_color(color),
                fontweight='bold',
            )

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(y_labels, fontsize=10, color=TEXT)
    ax.set_xlim(2020.5, 2029)
    ax.set_xticks(range(2021, 2030))
    ax.set_xlabel('年份', fontsize=10, color=TEXT)
    ax.set_title('图 23.1  超大规模云厂商 (CSP) 自研 AI ASIC 量产路线', fontsize=13, color=TEXT, fontweight='bold', pad=12)
    ax.grid(axis='x', color='#D8D8D8', linestyle='--', linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ax.invert_yaxis()
    return _save(fig, 'fig_v7_csp_asic_gantt')


# ============================================================
# 图 9: 国产化率分环节柱状图 (卷十)
# ============================================================
def fig_localization_bars():
    fig, ax = plt.subplots(figsize=(12, 6.5))
    fig.patch.set_facecolor(BG)
    _style(ax, title='图 38.1  半导体产业链各环节国产化率 (2024-2025 估计) 与突破目标',
           xlabel='', ylabel='国产化率 (%)')

    segs = ['设计 SoC', '设计 模拟', 'EDA 工具', '制造 28nm+', '制造 14nm-', '制造 7nm-',
            '设备 整体', '设备 光刻', '材料 整体', '高端材料', '封测']
    current = [72, 45, 12, 70, 25, 5, 35, 3, 50, 18, 80]
    target_2030 = [85, 70, 35, 90, 55, 20, 65, 30, 75, 50, 92]

    x = np.arange(len(segs))
    ax.bar(x - 0.2, current, 0.4, color=TEAL, label='2024-2025 现状', alpha=0.9)
    ax.bar(x + 0.2, target_2030, 0.4, color=GOLD, label='2030 突破目标', alpha=0.9)

    for i, (c, t) in enumerate(zip(current, target_2030)):
        ax.text(i - 0.2, c + 1.5, f'{c}%', ha='center', fontsize=8, color=TEAL, fontweight='bold')
        ax.text(i + 0.2, t + 1.5, f'{t}%', ha='center', fontsize=8, color=GOLD, fontweight='bold')
        gap = t - c
        if gap >= 20:
            ax.annotate('', xy=(i + 0.2, t - 2), xytext=(i - 0.2, c + 2),
                        arrowprops=dict(arrowstyle='->', color=RED, lw=1.2, alpha=0.6))

    ax.set_xticks(x)
    ax.set_xticklabels(segs, fontsize=9, color=TEXT, rotation=20, ha='right')
    ax.set_ylim(0, 105)
    ax.legend(loc='upper right', fontsize=9, frameon=False)
    ax.text(5, 95, '红箭头标记: 缺口超过 20 个百分点的"卡脖子"环节',
            fontsize=9, color=RED, style='italic')
    return _save(fig, 'fig_v10_localization_bars')


# ============================================================
# 图 10: 附录 G 估值周期阶段 (附录)
# ============================================================
def fig_valuation_cycle():
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.5, 4.5)
    ax.axis('off')

    # 正弦波
    x = np.linspace(0.5, 9.5, 500)
    y = 1.8 * np.sin((x - 0.5) / 9 * 2 * np.pi) + 1
    ax.plot(x, y, color=TEAL, linewidth=2.5)

    # 阶段标注
    phases = [
        (1.3, 'I. 萧条 / 估值见底',  '估值处于自身历史低位\n库存出清, 资本开支下行',  GREEN),
        (3.3, 'II. 复苏 / 估值修复', '订单回暖, EPS 拐点\n板块 Beta > 大盘',         GOLD),
        (5.3, 'III. 繁荣 / 估值溢价','估值扩张, 拥挤度上升\n龙头业绩兑现 + 资金面共振', RED),
        (7.3, 'IV. 衰退 / 估值杀',  '产能过剩信号 + 价格回落\n机构降仓位, 资金切换',  BROWN),
    ]
    for px, title, sub, color in phases:
        py = 1.8 * np.sin((px - 0.5) / 9 * 2 * np.pi) + 1
        ax.add_patch(Circle((px, py), 0.18, color=color, zorder=5))
        ax.text(px, py + 0.6, title, ha='center', fontsize=10.5, color=color, fontweight='bold')
        ax.text(px, py + 0.05 - 1.8, sub, ha='center', fontsize=8.5, color=TEXT)

    # 时间轴
    ax.annotate('', xy=(9.7, -0.5), xytext=(0.3, -0.5),
                arrowprops=dict(arrowstyle='->', color=MUTED, lw=1.5))
    ax.text(9.6, -0.7, '时间 →', fontsize=9, color=MUTED, ha='right')

    ax.text(5, 4.0, '图 G.1  半导体投资估值周期四阶段示意', ha='center', fontsize=13, color=TEXT, fontweight='bold')
    ax.text(5, 3.5, '阶段长度并不固定；AI 算力、存储、汽车与消费电子周期可能错峰叠加', ha='center', fontsize=9, color=MUTED, style='italic')

    return _save(fig, 'fig_g_valuation_cycle')


# ============================================================
# 图 11: AI Capex 产业链依赖与财务验证 (附录 G)
# ============================================================
def fig_ai_capex_flow():
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')

    ax.text(7, 7.4, '图 G.2  AI Capex 产业链依赖与财务验证链',
            ha='center', fontsize=13, color=TEXT, fontweight='bold')
    ax.text(7, 6.95, '公司级 Capex 披露 → 系统交付 → 芯片/封装 → 上游；每层都需独立验证',
            ha='center', fontsize=9.5, color=MUTED)

    # 4 层节点
    sources = [('Microsoft FY25', 'PP&E $64.6B'), ('Alphabet CY25', 'Capex $91.4B'),
               ('Amazon CY25', 'Cash Capex $128.3B'), ('Meta CY25', 'PP&E $69.7B')]
    layer1 = [('GPU 系统', '整机出货 × ASP', TEAL),
              ('CSP 自研 ASIC', '部署量 × 单机用量', GOLD),
              ('网络/存储/电力', '拓扑 × 配置', BLUE)]
    layer2 = [('HBM', '容量 × ASP × 份额', PURPLE),
              ('先进逻辑代工', '晶圆量 × ASP × 良率', BROWN),
              ('先进封装', '封装量 × 单价 × 良率', RED)]
    layer3 = [('EUV/High-NA 光刻', '订单 → 出货 → 验收', '#446688'),
              ('刻蚀/沉积/CMP 设备', '产能 × 工艺步骤', '#7B6B5C'),
              ('光罩/光刻胶/材料', '投片量 × 单耗', '#6F6256')]

    def draw_layer(items, y, label):
        ax.text(0.3, y, label, fontsize=10, color=MUTED, va='center',
                fontweight='bold', zorder=3)
        w = 13.0 / len(items)
        boxes = []
        for i, item in enumerate(items):
            if len(item) == 2:
                name, val = item; color = TEAL
            else:
                name, val, color = item
            x0 = 1.0 + i * w
            ax.add_patch(FancyBboxPatch((x0, y - 0.45), w - 0.3, 0.9, boxstyle='round,pad=0.03',
                                          facecolor=color, edgecolor='none', zorder=2))
            text_color = _readable_text_color(color)
            ax.text(x0 + (w - 0.3)/2, y + 0.10, name, ha='center', va='center',
                    fontsize=9, color=text_color, fontweight='bold', zorder=3)
            ax.text(x0 + (w - 0.3)/2, y - 0.25, val, ha='center', va='center',
                    fontsize=8.8, color=text_color, fontweight='bold', zorder=3)
            boxes.append((x0 + (w - 0.3)/2, y))
        return boxes

    b0 = draw_layer(sources, 6.0, '公司级披露')
    b1 = draw_layer(layer1, 4.5, '系统交付')
    b2 = draw_layer(layer2, 3.0, '芯片 + 封装')
    b3 = draw_layer(layer3, 1.5, '上游设备/材料')

    # 简化连接：source → layer1
    for src in b0:
        for tgt in b1:
            ax.annotate('', xy=(tgt[0], tgt[1] + 0.45), xytext=(src[0], src[1] - 0.45),
                        arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.5, alpha=0.25),
                        zorder=0)
    for src in b1:
        for tgt in b2:
            ax.annotate('', xy=(tgt[0], tgt[1] + 0.45), xytext=(src[0], src[1] - 0.45),
                        arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.7, alpha=0.35),
                        zorder=0)
    for src in b2:
        for tgt in b3:
            ax.annotate('', xy=(tgt[0], tgt[1] + 0.45), xytext=(src[0], src[1] - 0.45),
                        arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.7, alpha=0.35),
                        zorder=0)

    ax.text(7, 0.3, '* 上层为 2025 公司年报口径，非纯 AI 支出；财年与口径不同，不可直接求和或与下层做资金守恒',
            ha='center', fontsize=8, color=MUTED, style='italic')
    return _save(fig, 'fig_g_ai_capex_flow')


# ============================================================
# 图 12: 全球晶圆代工市场份额 (卷四)
# ============================================================
def fig_foundry_share():
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    labels = ['TSMC\n台积电', 'Samsung\nFoundry', 'SMIC\n中芯国际', 'UMC\n联电', 'GlobalFoundries', 'HuaHong\n华虹', 'PSMC / VIS / Tower 其他']
    sizes = [62, 11, 6, 5, 5, 3, 8]
    colors = [TEAL, GOLD, RED, BLUE, BROWN, '#A0526B', '#9A9A9A']

    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                       startangle=90, pctdistance=0.78,
                                       textprops={'fontsize': 9.5, 'color': TEXT, 'fontweight': 'bold'},
                                       wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    for wedge, at in zip(wedges, autotexts):
        at.set_color(_readable_text_color(wedge.get_facecolor()))
        at.set_fontweight('bold')
        at.set_fontsize(9)

    # 中心
    ax.add_patch(Circle((0, 0), 0.45, color=BG))
    ax.text(0, 0.08, '2024 全球', ha='center', fontsize=11, color=TEXT, fontweight='bold')
    ax.text(0, -0.12, '纯代工市场', ha='center', fontsize=11, color=TEXT, fontweight='bold')

    ax.set_title('图 13.1  全球纯代工 (Pure-Play Foundry) 市场份额\n(2024 年, 来源 TrendForce)',
                 fontsize=13, color=TEXT, pad=12, fontweight='bold')
    return _save(fig, 'fig_v4_foundry_share')


# ============================================================
# 图 13: ASML / Lam / AMAT / KLA 设备厂收入对比 (卷四)
# ============================================================
def fig_equipment_vendors():
    fig, ax = plt.subplots(figsize=(11, 5.5))
    fig.patch.set_facecolor(BG)
    _style(ax, title='图 12.1  全球前道设备五巨头收入对比 (2020-2024, USD bn)',
           xlabel='年份', ylabel='年收入 (USD bn)')

    years = ['2020', '2021', '2022', '2023', '2024']
    vendors = {
        'ASML (光刻)':           [16, 22, 24, 30, 32],
        'Applied Materials':     [17, 23, 26, 26, 27],
        'Lam Research':          [10, 17, 19, 14, 16],
        'Tokyo Electron':        [12, 18, 19, 16, 18],
        'KLA (量测/检测)':        [6,  9,  11, 10, 11],
    }
    colors = [TEAL, GOLD, BLUE, BROWN, PURPLE]
    x = np.arange(len(years))
    width = 0.16

    for i, (name, vals) in enumerate(vendors.items()):
        ax.bar(x + (i - 2)*width, vals, width, label=name, color=colors[i], alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=10, color=TEXT)
    ax.legend(loc='upper left', fontsize=9, frameon=False, ncol=2)
    return _save(fig, 'fig_v4_equipment_vendors')


# ============================================================
# 主流程
# ============================================================
FIGURE_BUILDERS = {
    'localization-radar': fig_localization_radar,
    'industry-overview': fig_industry_overview,
    'node-roadmap': fig_node_roadmap,
    'litho-roadmap': fig_litho_roadmap,
    'foundry-share': fig_foundry_share,
    'equipment-vendors': fig_equipment_vendors,
    'packaging-quadrant': fig_packaging_quadrant,
    'hbm-evolution': fig_hbm_evolution,
    'ai-chip-bubble': fig_ai_chip_bubble,
    'csp-asic-gantt': fig_csp_asic_gantt,
    'localization-bars': fig_localization_bars,
    'valuation-cycle': fig_valuation_cycle,
    'ai-capex-flow': fig_ai_capex_flow,
}


def _parse_args():
    parser = argparse.ArgumentParser(description='生成芯片产业链报告的 13 张插图。')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f'输出目录（默认：{DEFAULT_OUT_DIR}）',
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=DEFAULT_DPI,
        help=f'PNG 分辨率（默认：{DEFAULT_DPI}）',
    )
    parser.add_argument(
        '--figure',
        action='append',
        choices=FIGURE_BUILDERS,
        dest='figures',
        help='只生成指定图；可重复传入。默认生成全部。',
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='列出可用图表标识后退出。',
    )
    args = parser.parse_args()
    if args.dpi < 72:
        parser.error('--dpi 不能低于 72')
    return args


def main():
    global OUT_DIR, OUTPUT_DPI

    args = _parse_args()
    if args.list:
        print('\n'.join(FIGURE_BUILDERS))
        return

    _configure_cjk_font()
    OUT_DIR = args.output_dir.expanduser().resolve()
    OUTPUT_DPI = args.dpi
    selected = args.figures or list(FIGURE_BUILDERS)

    print(f'生成 {len(selected)} 张报告插图 → {OUT_DIR}')
    for figure_name in selected:
        FIGURE_BUILDERS[figure_name]()
    print('\n全部完成。')


if __name__ == '__main__':
    main()
