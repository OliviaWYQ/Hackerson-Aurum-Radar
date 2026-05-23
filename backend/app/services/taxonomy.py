"""Domain taxonomy & tunable knowledge for the Agent pipeline.

Keyword maps and scoring weights live here so they can be tuned without
touching stage logic. Aligned with prd/prd.md, backend/architecture.md §7.3 and
backend/preclassify_extract.md.
"""
from __future__ import annotations

from app.schemas.enums import (
    CredibilityLevel,
    EnvFactorId,
    Priority,
    SignalDirection,
    SourceCategory,
    SourceType,
)

# --- markets (MVP scope: architecture.md §1) -------------------------------
# Market codes are ISO-3166 alpha-2 (plus the synthetic "GLOBAL" bucket for
# multi-region or global-scope sources). data_probe writes these directly,
# the council / dashboard / frontend read these. Display names live in
# MARKET_DISPLAY_NAME so the UI can render the human-readable form.
MVP_MARKETS: list[str] = [
    "SG", "TH", "JP", "US", "KR", "ID", "MY", "VN", "PH", "GLOBAL",
]

MARKET_REGION: dict[str, str] = {
    "SG": "Southeast Asia",
    "TH": "Southeast Asia",
    "ID": "Southeast Asia",
    "MY": "Southeast Asia",
    "VN": "Southeast Asia",
    "PH": "Southeast Asia",
    "JP": "East Asia",
    "KR": "East Asia",
    "CN": "East Asia",
    "US": "North America",
    "IN": "South Asia",
    "GLOBAL": "Global",
}

# Human-readable display names — frontend prefers Chinese, falls back to code.
MARKET_DISPLAY_NAME: dict[str, str] = {
    "SG": "新加坡",
    "TH": "泰国",
    "JP": "日本",
    "US": "美国",
    "KR": "韩国",
    "ID": "印尼",
    "MY": "马来西亚",
    "VN": "越南",
    "PH": "菲律宾",
    "CN": "中国",
    "IN": "印度",
    "GLOBAL": "全球",
}

# Minimum raw_documents in the window before a market is worth running the
# council on — avoids burning LLM cost on markets with 1-2 stray articles.
MIN_DOCS_PER_MARKET: int = 10

# Default rolling window for dashboard + run_council queries (architecture.md §7).
DEFAULT_WINDOW_DAYS: int = 30

# --- relevance filter (stage 2) --------------------------------------------
# A document must mention at least one of these to be jewellery-relevant.
JEWELLERY_KEYWORDS: list[str] = [
    "jewellery", "jewelry", "gold", "diamond", "jade", "luxury",
    "watch", "bridal", "wedding", "bullion", "gemstone", "precious metal",
    "珠宝", "黄金", "钻石", "翡翠", "婚庆", "首饰",
]

# --- rule pre-classification (stage 3) -------------------------------------
# Keyword -> candidate SourceCategory. The LLM may override (pre_label is a hint).
KEYWORD_SOURCE_CATEGORY: dict[SourceCategory, list[str]] = {
    SourceCategory.competition: [
        "cartier", "tiffany", "van cleef", "bvlgari", "bulgari", "pandora",
        "harry winston", "chow tai fook", "luk fook", "chow sang sang",
        "老铺", "六福", "周生生", "周大福", "signet", "kay", "zales",
        "acquire", "acquisition", "merger", "市占", "并购",
    ],
    SourceCategory.product: [
        "collection", "launch", "new design", "lab-grown", "lab grown",
        "lab diamond", "lab-created", "lightweight", "craftsmanship",
        "古法金", "工艺", "设计", "新品",
    ],
    SourceCategory.social_media: [
        "tiktok", "instagram", "viral", "influencer", "kol", "social media",
        "种草", "小红书", "douyin", "抖音", "话题",
    ],
    SourceCategory.regulation: [
        "customs", "regulation", "regulatory", "import", "compliance",
        "money laundering", "aml", "kyc", "tax", "duty", "tariff",
        "declare", "hs code", "碳税", "认证", "禁令", "监管", "合规", "法规",
    ],
    SourceCategory.channel: [
        "boutique", "flagship", "opens", "opening", "new store", "mall",
        "airport", "duty free", "duty-free", "pop-up", "popup", "retail",
        "shopee", "lazada", "tiktok shop", "marketplace", "e-commerce",
        "platform", "seller", "commission", "fee", "门店", "渠道",
    ],
    SourceCategory.macro: [
        "gold price", "bullion", "gold rally", "per ounce", "per oz",
        "price surge", "exchange rate", "usd", "interest rate", "rate cut",
        "rate hike", "inflation", "gdp", "pmi", "金价", "汇率", "利率",
        "通胀", "降息",
    ],
    SourceCategory.supply_chain: [
        "mining", "mine", "miner", "alrosa", "de beers", "rough diamond",
        "smelter", "refinery", "production capacity", "output", "logistics",
        "shipping", "矿产", "产能", "供应链", "断供", "减产",
    ],
}

# --- env factor keyword hints (preclassify_extract.md §第二坐标轴) ---------
# Used to seed the LLM with candidate factors. The LLM still makes the final call.
ENV_FACTOR_KEYWORDS: dict[EnvFactorId, list[str]] = {
    EnvFactorId.F1: [   # 供给约束
        "制裁", "产区", "减产", "断供", "产能扩张", "库存积压",
        "sanction", "shortage", "rough diamond", "supply",
    ],
    EnvFactorId.F2: [   # 结构重塑
        "转型", "退出", "并购", "颠覆", "全面切换", "dtc",
        "acquisition", "merger", "pivot", "spin-off",
    ],
    EnvFactorId.F3: [   # 需求迁移
        "z世代", "悦己", "自购", "婚庆下滑", "新场景", "情绪消费",
        "gen z", "self-gifting", "bridal decline",
    ],
    EnvFactorId.F4: [   # 制度摩擦
        "新规", "hs编码", "碳税", "认证", "禁令", "冲突矿产",
        "compliance", "regulation", "tariff", "ban", "conflict mineral",
    ],
    EnvFactorId.F5: [   # 价格传导
        "金价", "美元", "降息", "通胀", "期货", "贵金属",
        "gold price", "usd", "rate cut", "inflation", "futures",
    ],
    EnvFactorId.F6: [   # 叙事压力
        "可持续", "esg", "品牌危机", "舆论发酵", "kol", "争议",
        "sustainable", "esg", "controversy", "backlash",
    ],
    EnvFactorId.F7: [   # 渠道博弈
        "直播", "平台佣金", "门店关闭", "dtc", "私域", "渠道下沉",
        "livestream", "platform fee", "store closure", "dtc", "channel",
    ],
}

# --- source credibility (stage 2), architecture.md §9 / PRD §9.4 ----------
# Per-source credibility, keyed by a case-insensitive substring of source_name.
SOURCE_CREDIBILITY: dict[str, CredibilityLevel] = {
    # S — 政府 / 监管 / 平台官方公告
    "customs": CredibilityLevel.S,
    "monetary authority": CredibilityLevel.S,
    "shopee help": CredibilityLevel.S,
    "tiktok shop": CredibilityLevel.S,
    "world gold council": CredibilityLevel.S,
    # A — 主流权威媒体 / 权威机构
    "straits times": CredibilityLevel.A,
    "business times": CredibilityLevel.A,
    "channel news asia": CredibilityLevel.A,
    "reuters": CredibilityLevel.A,
    "bloomberg": CredibilityLevel.A,
    "yahoo finance": CredibilityLevel.A,
    # B — 垂直 / 区域媒体、品牌官网、商场
    "vnexpress": CredibilityLevel.B,
    "vietnam+": CredibilityLevel.B,
    "malay mail": CredibilityLevel.B,
    "cna luxury": CredibilityLevel.B,
    "cna lifestyle": CredibilityLevel.B,
    "alvinology": CredibilityLevel.B,
    "sassy mama": CredibilityLevel.B,
    "vogue": CredibilityLevel.B,
    "tatler": CredibilityLevel.B,
    "tiffany": CredibilityLevel.B,
    "cartier": CredibilityLevel.B,
    "chow tai fook": CredibilityLevel.B,
}

# fallback by source_type when source_name is not matched above
DEFAULT_CREDIBILITY: dict[SourceType, CredibilityLevel] = {
    SourceType.regulation: CredibilityLevel.S,
    SourceType.platform: CredibilityLevel.S,
    SourceType.market_data: CredibilityLevel.A,
    SourceType.news: CredibilityLevel.A,
    SourceType.report: CredibilityLevel.A,
    SourceType.competitor: CredibilityLevel.B,
    SourceType.mall: CredibilityLevel.B,
    SourceType.social: CredibilityLevel.C,
}

# numeric rank (lower = more credible) — for comparison / dedup tie-break
CREDIBILITY_RANK: dict[CredibilityLevel, int] = {
    CredibilityLevel.S: 0,
    CredibilityLevel.A: 1,
    CredibilityLevel.B: 2,
    CredibilityLevel.C: 3,
}


def credibility_for(source_name: str | None, source_type: SourceType) -> CredibilityLevel:
    """Resolve credibility — by source name first, else by source_type."""
    name = (source_name or "").lower()
    for key, level in SOURCE_CREDIBILITY.items():
        if key in name:
            return level
    return DEFAULT_CREDIBILITY.get(source_type, CredibilityLevel.B)


# --- rule scoring (stage 4, architecture.md §7.3 与 preclassify_extract.md 接口约定) ---
# Stage 4 input is Stage 3 output, so the scorer keys off env_factor (impact mechanism)
# rather than source_category (channel).
#
# Per-factor (opportunity_bias, risk_bias) — defaults used when the env_factor's
# typical direction is honoured (e.g. F5 price_conduction is typically a risk).
ENV_FACTOR_BASE_BIAS: dict[EnvFactorId, tuple[int, int]] = {
    EnvFactorId.F1: (30, 70),   # 供给约束 — 成本/毛利风险为主
    EnvFactorId.F2: (55, 55),   # 结构重塑 — 双向，看跟随还是被颠覆
    EnvFactorId.F3: (60, 40),   # 需求迁移 — 偏机会（新品类替代旧品类）
    EnvFactorId.F4: (25, 75),   # 制度摩擦 — 合规成本，风险为主
    EnvFactorId.F5: (40, 60),   # 价格传导 — 偏风险
    EnvFactorId.F6: (40, 60),   # 叙事压力 — 偏风险（品牌侵蚀）
    EnvFactorId.F7: (55, 50),   # 渠道博弈 — 双向
}

# Signal direction shifts which dimension dominates (preclassify_extract.md §market direction)
SIGNAL_DIRECTION_ADJUSTMENT: dict[SignalDirection, tuple[int, int]] = {
    SignalDirection.positive: (+20, -10),
    SignalDirection.negative: (-10, +25),
    SignalDirection.mixed: (+5, +5),
    SignalDirection.neutral: (0, 0),
}

# A weak source yields a weaker score — we are less sure the signal is real.
CREDIBILITY_MULTIPLIER: dict[CredibilityLevel, float] = {
    CredibilityLevel.S: 1.0,
    CredibilityLevel.A: 0.92,
    CredibilityLevel.B: 0.78,
    CredibilityLevel.C: 0.60,
}

# Priority adjustment, applied to the dominant dimension
PRIORITY_ADJUSTMENT: dict[Priority, int] = {
    Priority.P0: 15,
    Priority.P1: 5,
    Priority.P2: -10,
}

# intensity (1-5) -> base multiplier (preclassify_extract.md §interface contract)
INTENSITY_MULTIPLIER: dict[int, float] = {
    1: 0.5,
    2: 0.7,
    3: 0.85,
    4: 1.0,
    5: 1.15,
}

# conduction lag_estimate keyword -> recency weight (best-effort fuzzy match)
LAG_RECENCY_WEIGHT: dict[str, float] = {
    "short": 1.0, "短期": 1.0, "周级": 1.0,
    "mid": 0.9, "中期": 0.9, "月级": 0.9,
    "long": 0.75, "长期": 0.75, "季度": 0.75, "年级": 0.7,
}


def region_for(market: str) -> str:
    """Best-effort region lookup for a market."""
    return MARKET_REGION.get(market, "Unknown")


def display_name_for(market: str) -> str:
    """Human-readable name for a market code; falls back to the code."""
    return MARKET_DISPLAY_NAME.get(market, market)
