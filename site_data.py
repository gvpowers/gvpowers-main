"""Central site content for the GV POWERS corporate website.

Only verified company facts are used here. Project statistics are managed
dynamically from the admin dashboard (database.py counts) — the homepage
figures are no longer hardcoded.
"""

COMPANY = {
    "name": "GV POWERS",
    "tagline": "Powering A Better Tomorrow",
    "established": 1997,
    "email": "gvpowerssalem@gmail.com",
    "phone_primary": "9894079090",
    "phone_primary_display": "+91 98940 79090",
    "phone_secondary": "9894079095",
    "phone_secondary_display": "+91 98940 79095",
    "whatsapp": "919894079090",
    "hours": "9:00 AM – 9:00 PM",
    "hours_schema": "Mo-Su 09:00-21:00",
    "locations": ["Chennai", "Salem"],
    "salem_address_note": (
        "No. 10, Kadharkhan Street, Opp. Railway Junction, Salem – 636 005 "
        "(historical record — to be confirmed before publication)"
    ),
}

# Verified sales achievements (not project-location counts, which are dynamic)
SOLD = [
    {"value": 1250, "display": "1,250+", "label": "UPS Sold", "icon": "battery"},
    {"value": 1800, "display": "1,800+", "label": "Generators Sold", "icon": "power"},
]

SERVICE_CHOICES = [
    ("solar", "Solar Energy"),
    ("ups", "UPS Systems"),
    ("generators", "Generators"),
    ("bess", "Battery Energy Storage"),
    ("amc", "AMC / Service"),
    ("general", "General Enquiry"),
]

NAV_LINKS = [
    {"label": "Home", "endpoint": "main.index"},
    {"label": "About", "endpoint": "main.about"},
    {"label": "Solutions", "endpoint": "main.solutions", "dropdown": [
        {"label": "Solar Energy", "endpoint": "main.solar"},
        {"label": "UPS Systems", "endpoint": "main.ups"},
        {"label": "Generators", "endpoint": "main.generators"},
        {"label": "Battery Energy Storage", "endpoint": "main.solutions", "anchor": "#battery-storage"},
    ]},
    {"label": "Projects", "endpoint": "main.projects"},
    {"label": "Contact", "endpoint": "main.contact"},
]
