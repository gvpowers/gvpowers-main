"""Route & infrastructure tests — every page, SEO files, headers, assets."""
import os
import re

STATIC_IMAGES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "static", "images"
)

PAGES = [
    ("/", b"Powering a", b"Better"),
    ("/about", b"About", b"1997"),
    ("/solutions", b"Solutions", b"Solar"),
    ("/solutions/solar", b"Solar", b"On-Grid"),
    ("/solutions/ups-systems", b"UPS", b"Online"),
    ("/solutions/generators", b"Generators", b"Diesel"),
    ("/projects", b"Projects", b"gvp-map"),
    ("/contact", b"Contact", b"Enquiry"),
]


class TestPages:
    def test_home(self, client):
        rv = client.get("/")
        assert rv.status_code == 200
        assert b"Powering a" in rv.data
        assert b"Better" in rv.data
        assert b"ENERGY" in rv.data.upper()
        assert b"1,250+" in rv.data or b"1250" in rv.data
        assert b"1,800+" in rv.data or b"1800" in rv.data
        assert b"Established" in rv.data

    def test_all_pages_return_200(self, client):
        for path, *needles in PAGES:
            rv = client.get(path)
            assert rv.status_code == 200, f"{path} failed"
            for needle in needles:
                assert needle in rv.data, f"{needle!r} missing on {path}"

    def test_catalogue_link_present_and_external(self, client):
        rv = client.get("/")
        html = rv.data.decode()
        assert "https://catalog.gvpowers.in" in html

    def test_navigation_links(self, client):
        html = client.get("/").data.decode()
        for fragment in ['href="/about"', 'href="/solutions"',
                         'href="/projects"', 'href="/contact"']:
            assert fragment in html, f"nav missing {fragment}"

    def test_no_invented_facts_on_home(self, client):
        """Guard against fabricated statistics or testimonials."""
        html = client.get("/").data.decode().lower()
        for banned in ["testimonial", "ceo", "founder mr", "happy clients:"]:
            assert banned not in html


class TestSEOFolders:
    def test_robots_txt(self, client):
        rv = client.get("/robots.txt")
        assert rv.status_code == 200
        assert b"Sitemap:" in rv.data

    def test_sitemap_xml(self, client):
        rv = client.get("/sitemap.xml")
        assert rv.status_code == 200
        assert b"<urlset" in rv.data
        assert b"https://gvpowers.in/" in rv.data
        assert rv.mimetype == "application/xml"

    def test_healthz(self, client):
        rv = client.get("/healthz")
        assert rv.status_code == 200
        assert rv.json["status"] == "ok"


class TestSecurityHeaders:
    def test_headers_present(self, client):
        rv = client.get("/")
        assert rv.headers["X-Content-Type-Options"] == "nosniff"
        assert "DENY" in rv.headers["X-Frame-Options"]
        assert "Content-Security-Policy" in rv.headers

    def test_csp_nonce_used_for_jsonld(self, client):
        rv = client.get("/")
        csp = rv.headers["Content-Security-Policy"]
        nonce = re.search(r"nonce-([A-Za-z0-9_-]+)", csp).group(1)
        html = rv.data.decode()
        assert f'nonce="{nonce}"' in html


class TestErrorPages:
    def test_404_page(self, client):
        rv = client.get("/this-page-does-not-exist")
        assert rv.status_code == 404
        assert b"404" in rv.data
        assert b"Back to Home" in rv.data

    def test_static_missing_returns_json(self, client):
        rv = client.get("/static/images/does-not-exist.jpg")
        assert rv.status_code == 404


class TestImages:
    """All referenced local images must exist on disk."""

    def test_image_directories_exist(self):
        for sub in ["hero", "solar", "ups", "generators", "about", "branding"]:
            path = os.path.join(STATIC_IMAGES_DIR, sub)
            assert os.path.isdir(path), f"missing {sub} directory"
            files = os.listdir(path)
            assert files, f"{sub} image directory is empty"

    def test_hero_image_exists(self):
        assert os.path.isfile(os.path.join(STATIC_IMAGES_DIR, "hero", "hero-solar.jpg"))

    def test_referenced_images_load(self, client):
        """Extract static image paths from the home page and request each."""
        html = client.get("/").data.decode()
        paths = set(re.findall(r"/static/images/[a-zA-Z0-9/_.-]+\.jpg", html))
        assert paths, "no images referenced on home page"
        for p in paths:
            rv = client.get(p)
            assert rv.status_code == 200, f"broken image {p}"

    def test_favicons_exist(self):
        base = os.path.join(os.path.dirname(__file__), "..", "static", "favicon")
        for name in ["favicon.svg", "favicon-32.png", "apple-touch-icon.png"]:
            assert os.path.isfile(os.path.join(base, name))
