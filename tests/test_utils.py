import alert_system
from fetch_data import extract_headline
from market_utils import get_currency_symbol


def test_currency_symbols():
    assert get_currency_symbol("AAPL") == "$"
    assert get_currency_symbol("INFY.NS") == "₹"
    assert get_currency_symbol("tatasteel.bo") == "₹"
    assert get_currency_symbol("^NSEI") == "₹"
    assert get_currency_symbol("VOD.L") == "£"


def test_extract_headline_both_yahoo_formats():
    assert extract_headline({"content": {"title": "Nested"}}) == "Nested"
    assert extract_headline({"title": "Flat"}) == "Flat"
    assert extract_headline({"id": 1}) is None


def test_alert_filter_and_html_escaping():
    data = [
        {"ticker": "A", "price": 1.0, "sentiment": "negative", "confidence": 0.95, "headline": "<script>x</script>"},
        {"ticker": "B", "price": 1.0, "sentiment": "negative", "confidence": 0.5, "headline": "weak"},
        {"ticker": "C", "price": 1.0, "sentiment": "positive", "confidence": 0.99, "headline": "good"},
    ]
    alerts = alert_system.find_alerts(data)
    assert [a["ticker"] for a in alerts] == ["A"]
    html = alert_system.build_alert_html(alerts)
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_alert_without_email_credentials_does_not_crash(capsys):
    alert_system.send_market_alert([
        {"ticker": "T", "price": 1.0, "sentiment": "negative", "confidence": 0.9, "headline": "h"}
    ])
    assert "skipping email" in capsys.readouterr().out


def test_parse_rss_strips_publisher_and_sorts_newest_first():
    from fetch_data import parse_rss
    xml = b"""<rss><channel>
      <item><title>Old story - Reuters</title><pubDate>Mon, 26 Oct 2026 03:50:00 GMT</pubDate></item>
      <item><title>New story - Barron's</title><pubDate>Tue, 27 Oct 2026 09:30:00 GMT</pubDate></item>
    </channel></rss>"""
    items = parse_rss(xml, strip_source=True)
    assert [i["title"] for i in items] == ["New story", "Old story"]


def test_quote_pages_are_not_treated_as_news():
    from fetch_data import QUOTE_PAGE
    assert QUOTE_PAGE.search("HDFC Bank Share Price - Live NSE/BSE Updates")
    assert QUOTE_PAGE.search("Infosys Limited (INFY) stock price, news, quote and history")
    assert not QUOTE_PAGE.search("Infosys shares fall 6.6% after growth forecast cut")
    assert not QUOTE_PAGE.search("Why Nvidia's stock price could double, says analyst")
