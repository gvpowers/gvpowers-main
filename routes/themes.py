"""Registered website themes (id, label). CSS variants live in
static/css/themes/theme-<id>.css and are keyed by html[data-theme].

Each theme is a complete visual system (layout, nav, hero, cards, buttons,
footer treatment) — not merely a palette swap. Theme 09 (Glassmorphism Pro)
is the only theme where glassmorphism is a major design feature; the default
is a professional, non-glass system.
"""

THEMES = [
    {"id": "swiss-editorial", "label": "Swiss Editorial"},
    {"id": "luxury-heritage", "label": "Luxury Heritage"},
    {"id": "industrial-modern", "label": "Industrial Modern"},
    {"id": "corporate-minimal", "label": "Corporate Minimal"},
    {"id": "energy-technology", "label": "Energy Technology"},
    {"id": "dark-graphite", "label": "Dark Graphite"},
    {"id": "warm-monochrome", "label": "Warm Monochrome"},
    {"id": "swiss-grid", "label": "Swiss Grid"},
    {"id": "glassmorphism-pro", "label": "Glassmorphism Pro"},
    {"id": "neo-brutalist", "label": "Neo-Brutalist"},
    {"id": "classic-business", "label": "Classic Business"},
    {"id": "spatial-modern", "label": "Spatial Modern"},
    {"id": "nordic-minimal", "label": "Nordic Minimal"},
    {"id": "high-end-technology", "label": "High-End Technology"},
    {"id": "modern-energy-portfolio", "label": "Modern Energy Portfolio"},
]

THEME_IDS = {t["id"] for t in THEMES}
DEFAULT_THEME = "swiss-editorial"  # non-glass, professional default

# Theme ids used by earlier releases, mapped onto the current set.
# (A visitor's saved local preference and any stored admin default that
# still points at the old ids must resolve to a real theme.)
LEGACY_THEME_MAP = {
    "sage-glass": "glassmorphism-pro",   # the old default glass look
    "glass-pro": "glassmorphism-pro",
    "luxury-editorial": "luxury-heritage",
    "industrial": "industrial-modern",
    "architectural": "swiss-editorial",
    "corporate": "corporate-minimal",
    "monochrome": "warm-monochrome",
    "brutalist": "neo-brutalist",
    "classic": "classic-business",
    "spatial": "spatial-modern",
    "nordic": "nordic-minimal",
    "energy-tech": "high-end-technology",
    "energy-portfolio": "modern-energy-portfolio",
}


def canonical_theme(theme_id: str | None) -> str | None:
    """Map any legacy id onto a current id. Returns the canonical id or None."""
    if not theme_id:
        return None
    theme_id = theme_id.strip()
    if theme_id in THEME_IDS:
        return theme_id
    return LEGACY_THEME_MAP.get(theme_id)


def resolve_theme(theme_id: str | None) -> str:
    return canonical_theme(theme_id) or DEFAULT_THEME


def resolve_admin_default(theme_id: str | None) -> str:
    """Normalise a stored admin default.

    The historical glass defaults must not remain the site default for a
    non-glass redesign: legacy glass ids resolve to the new non-glass
    default, everything else keeps its own choice via the legacy map.
    """
    canonical = canonical_theme(theme_id)
    if canonical in ("glassmorphism-pro",):
        return DEFAULT_THEME
    return canonical or DEFAULT_THEME
