"""
v1.6 批量生成芯片产业链报告插图
- 统一配色 (与 PDF 设计语言对齐: TEAL #01696F, GOLD #D19900, BROWN #6E522B, BG #F7F6F2)
- 中文字体: Noto Sans CJK SC
- 输出: /home/user/workspace/figures/*.png  (高分辨率 200dpi)
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch, Wedge, Circle
import matplotlib.font_manager as fm
import numpy as np

# ---- 中文字体 ----
# 使用 NotoSansSC 本地 ttf (与 PDF builder 同一套)
CJK_REGULAR = '/home/user/workspace/fonts/NotoSansSC-Regular.ttf'
CJK_BOLD = '/home/user/workspace/fonts/NotoSansSC-Bold.ttf'
for fp in (CJK_REGULAR, CJK_BOLD):
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)

# fallback to system Noto CJK
for fp in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
           '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'):
    if os.path.exists(fp):
        try:
            fm.fontManager.addfont(fp)
        except Exception:
            pass

# 查实际可用 family
_avail = {f.name for f in fm.fontManager.ttflist}
for cand in ('Noto Sans SC', 'Noto Sans CJK SC', 'Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'DejaVu Sans'):
    if cand in _avail:
        plt.rcParams['font.family'] = [cand]
        print(f'using font: {cand}')
        break
plt.rcParams['axes.unicode_minus'] = False

# ---- 调色板 (财经/科技调) ----
TEAL = '#01696F'
TEAL_LIGHT = '#5BA8AC'
GOLD = '#D19900'
GOLD_LIGHT = '#E8C76A'
BROWN = '#6E522B'
BG = '#F7F6F2'
TEXT = '#2A2A2A'
MUTED = '#6A6A6A'
RED = '#B73E3E'
BLUE = '#2E5C8A'
GREEN = '#3F7A4A'
PURPLE = '#7A4A7A'

PALETTE = [TEAL, GOLD, BROWN, BLUE, GREEN, PURPLE, RED, TEAL_LIGHT, GOLD_LIGHT]

OUT_DIR = '/home/user/workspace/figures'
os.makedirs(OUT_DIR, exist_ok=True)


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
    path = os.path.join(OUT_DIR, name + '.png')
    fig.patch.set_facecolor(BG)
    fig.savefig(path, dpi=200, bbox_inches='tight', facecolor=BG)
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
                                      facecolor=color, edgecolor='none', alpha=0.85))
        ax.text(x0+1.25, y0+0.2, title, ha='center', va='center', fontsize=11, color='white', fontweight='bold')
        for i, (name, vol) in enumerate(items):
            yy = y0 - 0.9 - i*1.5
            ax.add_patch(FancyBboxPatch((x0, yy-0.55), 2.5, 1.1, boxstyle='round,pad=0.04',
                                          facecolor='white', edgecolor=color, linewidth=1.5))
            ax.text(x0+1.25, yy+0.15, name, ha='center', va='center', fontsize=10, color=TEXT, fontweight='bold')
            ax.text(x0+1.25, yy-0.32, vol, ha='center', va='center', fontsize=8.5, color=color, fontweight='bold')

    # 底部地缘政治带
    ax.add_patch(FancyBboxPatch((0.5, 0.3), 13.0, 0.7, boxstyle='round,pad=0.05',
                                  facecolor=RED, edgecolor='none', alpha=0.85))
    ax.text(7, 0.65, '卷十 · 地缘政治 / 产业政策 / 投资框架  ——  贯穿全链的宏观变量', ha='center', va='center',
            fontsize=11, color='white', fontweight='bold')

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
        (2020, 'N5 / 5nm\nFinFET 极限', '台积电', TEAL, 'top'),
        (2022, 'N3 / 3nm\nFinFET 最后一代', '台积电 / 三星', TEAL, 'bottom'),
        (2022, 'SF3 GAA\nNanosheet 首发', '三星', GOLD, 'top'),
        (2025, 'N2 / 2nm\nGAA Nanosheet', '台积电', GOLD, 'top'),
        (2025, '18A\nRibbonFET + BSPDN', 'Intel', BROWN, 'bottom'),
        (2026, 'A14 / 1.4nm', '台积电', GOLD, 'bottom'),
        (2027, '14A\nHigh-NA EUV', 'Intel', BROWN, 'top'),
        (2028, 'A10 / 1nm\nCFET 预研', '台积电', RED, 'top'),
        (2030, 'CFET 量产\n3D 堆叠晶体管', '行业目标', RED, 'bottom'),
    ]

    for year, label, vendor, color, side in milestones:
        y_label = 4.5 if side == 'top' else 1.0
        y_marker = 3.0 if side == 'top' else 2.7
        ax.plot([year, year], [y_marker, y_label - (0.3 if side == 'top' else -0.3)],
                color=color, linewidth=1.0, alpha=0.6)
        ax.add_patch(Circle((year, 2.86), 0.13, color=color, zorder=5))
        ax.add_patch(FancyBboxPatch((year - 0.55, y_label - 0.45), 1.1, 0.9, boxstyle='round,pad=0.02',
                                      facecolor='white', edgecolor=color, linewidth=1.3))
        ax.text(year, y_label + 0.15, label, ha='center', va='center', fontsize=8, color=TEXT, fontweight='bold')
        ax.text(year, y_label - 0.28, vendor, ha='center', va='center', fontsize=7, color=color)

    for y in range(2019, 2032, 2):
        ax.text(y, 2.4, str(y), ha='center', va='top', fontsize=9, color=MUTED, fontweight='bold')

    ax.text(2025, 5.5, '图 3.x  全球先进制程演进时间线 (FinFET → GAA Nanosheet → CFET)',
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
    _style(ax, title='图 4.x  EUV 光刻系统路线: NA / 单次曝光极限 / 量产节点',
           xlabel='年份', ylabel='单次曝光最小线宽 (nm)')

    years = [2019, 2021, 2023, 2025, 2027, 2030]
    line_width = [13.5, 13.0, 12.5, 8.5, 8.0, 5.5]  # 单次曝光极限 (nm) 简化口径

    # NA = 0.33 (NXE)
    ax.plot(years[:4], line_width[:4], 'o-', color=TEAL, linewidth=2.5, markersize=9,
            label='NXE:3400/3600 系列 (NA=0.33)')
    # High-NA 0.55
    ax.plot(years[3:], line_width[3:], 's-', color=GOLD, linewidth=2.5, markersize=9,
            label='EXE:5000 系列 (High-NA, NA=0.55)')
    # Hyper-NA 0.75 (虚线)
    ax.plot([2029, 2031], [5.5, 4.0], '^--', color=RED, linewidth=2, markersize=9, alpha=0.7,
            label='Hyper-NA (NA=0.75, 规划)')

    annotations = [
        (2019, 13.5, 'EUV 量产元年\nTSMC N7+'),
        (2023, 12.5, 'N3/N2 量产工具'),
        (2025, 8.5, 'High-NA 首台\nIntel 18A'),
        (2027, 8.0, '台积电 A14\n首批 High-NA'),
        (2030, 5.5, 'A10 / CFET\n双重曝光'),
    ]
    for x, y, t in annotations:
        ax.annotate(t, xy=(x, y), xytext=(x, y + 1.8), fontsize=8, ha='center', color=TEXT,
                    arrowprops=dict(arrowstyle='->', color=MUTED, lw=0.7))

    ax.legend(loc='upper right', fontsize=9, frameon=False)
    ax.set_xlim(2018, 2032)
    ax.set_ylim(0, 18)
    return _save(fig, 'fig_v4_litho_roadmap')


# ============================================================
# 图 5: 先进封装家族象限图 (卷五)
# ============================================================
def fig_packaging_quadrant():
    fig, ax = plt.subplots(figsize=(11, 8))
    fig.patch.set_facecolor(BG)
    _style(ax, title='图 5.x  先进封装家族: 互连密度 vs 集成层次',
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
    _style(ax, title='图 6.x  HBM 高带宽内存代际演进 (容量 / 带宽 / 堆叠层数)',
           xlabel='', ylabel='单 Stack 带宽 (GB/s)')

    gens = ['HBM2', 'HBM2E', 'HBM3', 'HBM3E', 'HBM4', 'HBM4E', 'HBM5']
    bw = [256, 460, 819, 1229, 2048, 2560, 4096]
    cap = [8, 16, 24, 36, 48, 64, 96]   # GB per stack
    layers = [8, 8, 12, 12, 16, 16, 20]
    years = [2018, 2020, 2022, 2024, 2026, 2027, 2029]

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
    ax2.set_ylim(0, 110)

    ax.set_xticks(x)
    ax.set_xticklabels([f'{g}\n({y}年 · {l} 层)' for g, y, l in zip(gens, years, layers)], fontsize=9.5, color=TEXT)
    ax.set_ylim(0, 4800)
    ax.legend(loc='upper left', fontsize=9, frameon=False)
    ax2.legend(loc='upper left', bbox_to_anchor=(0, 0.92), fontsize=9, frameon=False)
    return _save(fig, 'fig_v6_hbm_evolution')


# ============================================================
# 图 7: AI 芯片格局气泡图 (卷七)
# ============================================================
def fig_ai_chip_bubble():
    fig, ax = plt.subplots(figsize=(12, 7.5))
    fig.patch.set_facecolor(BG)
    _style(ax, title='图 7.x  AI 训练芯片格局: 算力 vs 显存 vs 单卡价格 (2024-2025)',
           xlabel='单卡 BF16 算力 (PFLOPS)', ylabel='HBM 显存容量 (GB)', grid_axis='both')

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

    for name, flops, hbm, price, color in chips:
        s = min(price, 80) * 18 + 50
        ax.scatter(flops, hbm, s=s, color=color, alpha=0.65, edgecolor='white', linewidth=1.5)
        ax.text(flops, hbm + 8, name, ha='center', fontsize=8, color=TEXT, fontweight='bold')

    ax.set_xlim(0, 5.5)
    ax.set_ylim(0, 420)

    # Legend (vendor)
    vendors = [('NVIDIA', TEAL), ('AMD', BLUE), ('Intel', BROWN), ('Google', GOLD),
               ('AWS', PURPLE), ('Cerebras', RED), ('华为', GREEN)]
    for i, (n, c) in enumerate(vendors):
        ax.scatter(0.2, 380 - i*22, s=180, color=c, alpha=0.7)
        ax.text(0.4, 380 - i*22, n, va='center', fontsize=9, color=TEXT)
    ax.text(2.0, 400, '气泡大小 ∝ 单卡价格 (Cerebras 为系统级)', fontsize=8.5, color=MUTED, style='italic')

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
            ax.text((s + e)/2, i, name, ha='center', va='center', fontsize=8.5, color='white', fontweight='bold')

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(y_labels, fontsize=10, color=TEXT)
    ax.set_xlim(2020.5, 2029)
    ax.set_xticks(range(2021, 2030))
    ax.set_xlabel('年份', fontsize=10, color=TEXT)
    ax.set_title('图 7.x  超大规模云厂商 (CSP) 自研 AI ASIC 量产路线', fontsize=13, color=TEXT, fontweight='bold', pad=12)
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
    _style(ax, title='图 10.x  半导体产业链各环节国产化率 (2024-2025 估计) 与突破目标',
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
        (1.3, 'I. 萧条 / 估值见底',  'PE/PB 历史 10% 分位以下\n库存出清, 资本开支下行',  GREEN),
        (3.3, 'II. 复苏 / 估值修复', '订单回暖, EPS 拐点\n板块 Beta > 大盘',         GOLD),
        (5.3, 'III. 繁荣 / 估值溢价','PE 70% 分位以上\n龙头业绩兑现 + 资金面共振', RED),
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

    ax.text(5, 4.0, '图 G.x  半导体投资估值周期四阶段示意', ha='center', fontsize=13, color=TEXT, fontweight='bold')
    ax.text(5, 3.5, '典型周期 3-4 年, AI 算力周期与传统消费/工业周期可能错峰叠加', ha='center', fontsize=9, color=MUTED, style='italic')

    return _save(fig, 'fig_g_valuation_cycle')


# ============================================================
# 图 11: AI Capex 产业链资金流向 (附录 G)
# ============================================================
def fig_ai_capex_flow():
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')

    ax.text(7, 7.4, '图 G.x  AI Capex 产业链资金流向 (2024-2025, 数量级估算)',
            ha='center', fontsize=13, color=TEXT, fontweight='bold')
    ax.text(7, 6.95, '北美四大超算云 (Hyperscaler) 资本开支 → 系统集成 → 芯片 → 上游设备/材料',
            ha='center', fontsize=9.5, color=MUTED)

    # 4 层节点
    sources = [('Microsoft', '~80B'), ('Google', '~75B'), ('Amazon AWS', '~85B'), ('Meta', '~40B')]
    layer1 = [('Nvidia 系统\n(B200/GB200/NVL72)', '~150B', TEAL),
              ('CSP 自研 ASIC\n(TPU/Trainium/Maia)', '~30B', GOLD),
              ('AMD/Intel/Other GPU', '~20B', BLUE)]
    layer2 = [('HBM\n(SK Hynix/三星/Micron)', '~35B', PURPLE),
              ('先进逻辑代工\n(TSMC N5/N4/N3)', '~50B', BROWN),
              ('先进封装\n(CoWoS/SoIC)', '~20B', RED)]
    layer3 = [('EUV/High-NA 光刻\n(ASML)', '~12B', '#446688'),
              ('刻蚀/沉积/CMP 设备', '~18B', '#7B6B5C'),
              ('光罩/光刻胶/材料', '~10B', '#8C7B6B')]

    def draw_layer(items, y, label):
        ax.text(0.3, y, label, fontsize=10, color=MUTED, va='center', fontweight='bold')
        w = 13.0 / len(items)
        boxes = []
        for i, item in enumerate(items):
            if len(item) == 2:
                name, val = item; color = TEAL
            else:
                name, val, color = item
            x0 = 1.0 + i * w
            ax.add_patch(FancyBboxPatch((x0, y - 0.45), w - 0.3, 0.9, boxstyle='round,pad=0.03',
                                          facecolor=color, alpha=0.85, edgecolor='none'))
            ax.text(x0 + (w - 0.3)/2, y + 0.10, name, ha='center', va='center', fontsize=9, color='white', fontweight='bold')
            ax.text(x0 + (w - 0.3)/2, y - 0.25, f'$ {val}', ha='center', va='center', fontsize=9.5, color='white', fontweight='bold')
            boxes.append((x0 + (w - 0.3)/2, y))
        return boxes

    b0 = draw_layer(sources, 6.0, '资金源头')
    b1 = draw_layer(layer1, 4.5, '系统集成')
    b2 = draw_layer(layer2, 3.0, '芯片 + 封装')
    b3 = draw_layer(layer3, 1.5, '上游设备/材料')

    # 简化连接：source → layer1
    for src in b0:
        for tgt in b1:
            ax.annotate('', xy=(tgt[0], tgt[1] + 0.45), xytext=(src[0], src[1] - 0.45),
                        arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.5, alpha=0.25))
    for src in b1:
        for tgt in b2:
            ax.annotate('', xy=(tgt[0], tgt[1] + 0.45), xytext=(src[0], src[1] - 0.45),
                        arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.7, alpha=0.35))
    for src in b2:
        for tgt in b3:
            ax.annotate('', xy=(tgt[0], tgt[1] + 0.45), xytext=(src[0], src[1] - 0.45),
                        arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.7, alpha=0.35))

    ax.text(7, 0.3, '* 金额为综合 Bloomberg / IDC / Counterpoint / SEMI 公开口径的近似估算，单位 USD',
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
    colors = [TEAL, GOLD, RED, BLUE, BROWN, '#A0526B', '#8C8C8C']

    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                       startangle=90, pctdistance=0.78,
                                       textprops={'fontsize': 9.5, 'color': TEXT, 'fontweight': 'bold'},
                                       wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    for at in autotexts:
        at.set_color('white')
        at.set_fontweight('bold')
        at.set_fontsize(9)

    # 中心
    ax.add_patch(Circle((0, 0), 0.45, color=BG))
    ax.text(0, 0.08, '2024 全球', ha='center', fontsize=11, color=TEXT, fontweight='bold')
    ax.text(0, -0.12, '纯代工市场', ha='center', fontsize=11, color=TEXT, fontweight='bold')

    ax.set_title('图 4.x  全球纯代工 (Pure-Play Foundry) 市场份额\n(2024 年, 来源 TrendForce)',
                 fontsize=13, color=TEXT, pad=12, fontweight='bold')
    return _save(fig, 'fig_v4_foundry_share')


# ============================================================
# 图 13: ASML / Lam / AMAT / KLA 设备厂收入对比 (卷四)
# ============================================================
def fig_equipment_vendors():
    fig, ax = plt.subplots(figsize=(11, 5.5))
    fig.patch.set_facecolor(BG)
    _style(ax, title='图 4.x  全球前道设备五巨头收入对比 (2020-2024, USD bn)',
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
if __name__ == '__main__':
    print('生成 v1.6 报告插图...')
    fig_localization_radar()
    fig_industry_overview()
    fig_node_roadmap()
    fig_litho_roadmap()
    fig_foundry_share()
    fig_equipment_vendors()
    fig_packaging_quadrant()
    fig_hbm_evolution()
    fig_ai_chip_bubble()
    fig_csp_asic_gantt()
    fig_localization_bars()
    fig_valuation_cycle()
    fig_ai_capex_flow()
    print('\n全部完成。')
