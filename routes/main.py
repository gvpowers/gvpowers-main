"""Core page routes: home, about, solutions, service pages, projects,
sitemap.xml and robots.txt. Project statistics are computed dynamically
from the admin-managed database (see database.get_counts)."""
from flask import Blueprint, Response, render_template, current_app

import database as db
from site_data import SOLD

main = Blueprint("main", __name__)


def build_home_stats() -> list:
    """Established year + dynamic project counts + verified sales figures."""
    counts = db.get_counts()
    return [
        {"value": 1997, "display": "1997", "suffix": "",
         "label": "Established", "icon": "history"},
        {"value": counts["solar"]["completed"],
         "display": f"{counts['solar']['completed']:,}", "suffix": "",
         "label": "Solar Projects Completed", "icon": "sun"},
        {"value": counts["solar"]["ongoing"],
         "display": f"{counts['solar']['ongoing']:,}", "suffix": "",
         "label": "Solar Projects Ongoing", "icon": "panel"},
        {"value": SOLD[0]["value"], "display": SOLD[0]["display"], "suffix": "+",
         "label": SOLD[0]["label"], "icon": "battery"},
        {"value": SOLD[1]["value"], "display": SOLD[1]["display"], "suffix": "+",
         "label": SOLD[1]["label"], "icon": "power"},
    ]


@main.route("/")
def index():
    return render_template("index.html", stats=build_home_stats())


@main.route("/about")
def about():
    return render_template("about.html", stats=build_home_stats())


@main.route("/solutions")
def solutions():
    return render_template("solutions.html")


@main.route("/solutions/solar")
def solar():
    return render_template("solar.html")


@main.route("/solutions/ups-systems")
def ups():
    return render_template("ups.html")


@main.route("/solutions/generators")
def generators():
    return render_template("generators.html")


@main.route("/projects")
def projects():
    counts = db.get_counts()
    return render_template("projects.html", counts=counts)


@main.route("/contact")
def contact():
    return render_template("contact.html", form_values={})


@main.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


@main.route("/sitemap.xml")
def sitemap():
    pages = [
        ("/", "1.0", "weekly"),
        ("/about", "0.8", "monthly"),
        ("/solutions", "0.9", "monthly"),
        ("/solutions/solar", "0.9", "monthly"),
        ("/solutions/ups-systems", "0.9", "monthly"),
        ("/solutions/generators", "0.9", "monthly"),
        ("/projects", "0.8", "monthly"),
        ("/contact", "0.7", "monthly"),
    ]
    xml = render_template("sitemap.xml", pages=pages)
    return Response(xml, mimetype="application/xml")


@main.route("/robots.txt")
def robots():
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {current_app.config['SITE_URL']}/sitemap.xml",
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")
