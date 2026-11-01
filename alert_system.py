import smtplib
import os
from html import escape
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")
# Alerts go to the admin address; defaults to sending to yourself
RECEIVER = os.getenv("EMAIL_RECEIVER") or SENDER


def find_alerts(data_list, min_confidence=0.7):
    """Rule: Sentiment is NEGATIVE AND Confidence > min_confidence"""
    return [item for item in data_list
            if item.get('sentiment') == 'negative' and item.get('confidence', 0) > min_confidence]


def build_alert_html(alerts):
    rows = "".join(f"""
                <tr>
                    <td style="border: 1px solid black; padding: 8px;"><b>{escape(str(item['ticker']))}</b></td>
                    <td style="border: 1px solid black; padding: 8px;">{item['price']:,.2f}</td>
                    <td style="border: 1px solid black; padding: 8px; color: red;">{item['confidence']:.2f}</td>
                    <td style="border: 1px solid black; padding: 8px;">{escape(str(item['headline']))}</td>
                </tr>""" for item in alerts)

    return f"""
    <html>
        <body>
            <h2>⚠️ Market Intelligence Report</h2>
            <p>The system detected <b>{len(alerts)} high-confidence negative signals</b> in your watchlist.</p>
            <table style="border: 1px solid black; border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <th style="border: 1px solid black; padding: 8px;">Ticker</th>
                    <th style="border: 1px solid black; padding: 8px;">Price</th>
                    <th style="border: 1px solid black; padding: 8px;">Confidence</th>
                    <th style="border: 1px solid black; padding: 8px;">Headline</th>
                </tr>{rows}
            </table>
            <p><i>- Sent by Market Sentinel Robot 🤖</i></p>
        </body>
    </html>
    """


def send_market_alert(data_list):
    """
    Filters the analyzed data for 'High Risk' items and sends an email if found.
    """
    print("--- 🔔 CHECKING FOR ALERTS ---")

    alerts = find_alerts(data_list)
    if not alerts:
        print("✅ No critical alerts found. Keeping silent.")
        return

    print(f"⚠️ Found {len(alerts)} critical alerts!")

    if not SENDER or not PASSWORD:
        print("ℹ️ EMAIL_SENDER / EMAIL_PASSWORD not set - skipping email.")
        return

    msg = EmailMessage()
    msg['Subject'] = f"🚨 Market Sentinel Alert: {len(alerts)} Critical Risks Detected"
    msg['From'] = SENDER
    msg['To'] = RECEIVER
    msg.set_content("Check your dashboard for alerts.") # Fallback for non-HTML clients
    msg.add_alternative(build_alert_html(alerts), subtype='html')

    # SEND VIA GMAIL SMTP
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER, PASSWORD)
            smtp.send_message(msg)
        print("📨 Email Alert Sent Successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


# Test Block
if __name__ == "__main__":
    # Fake data to test the email (same keys main.py produces)
    dummy_data = [
        {'ticker': 'TEST', 'price': 100, 'sentiment': 'negative', 'confidence': 0.95, 'headline': 'Test Crisis Event'}
    ]
    send_market_alert(dummy_data)
