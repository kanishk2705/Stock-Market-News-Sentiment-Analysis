import smtplib
import os
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")
# You can send it to yourself
RECEIVER = SENDER 

def send_market_alert(data_list):
    """
    Filters the analyzed data for 'High Risk' items and sends an email if found.
    """
    print("--- 🔔 CHECKING FOR ALERTS ---")
    
    # 1. FILTER: What counts as "Urgent"?
    # Rule: Sentiment is NEGATIVE AND Confidence > 0.7
    alerts = []
    for item in data_list:
        if item['Sentiment'] == 'negative' and item['Confidence'] > 0.7:
            alerts.append(item)
    
    if not alerts:
        print("✅ No critical alerts found. Keeping silent.")
        return

    print(f"⚠️ Found {len(alerts)} critical alerts! Sending email...")

    # 2. CONSTRUCT EMAIL (HTML)
    msg = EmailMessage()
    msg['Subject'] = f"🚨 Market Sentinel Alert: {len(alerts)} Critical Risks Detected"
    msg['From'] = SENDER
    msg['To'] = RECEIVER

    # Build a simple HTML Table
    html_body = f"""
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
                </tr>
    """
    
    for item in alerts:
        html_body += f"""
                <tr>
                    <td style="border: 1px solid black; padding: 8px;"><b>{item['Ticker']}</b></td>
                    <td style="border: 1px solid black; padding: 8px;">{item['Price']}</td>
                    <td style="border: 1px solid black; padding: 8px; color: red;">{item['Confidence']:.2f}</td>
                    <td style="border: 1px solid black; padding: 8px;">{item['Headline']}</td>
                </tr>
        """
    
    html_body += """
            </table>
            <p><i>- Sent by Market Sentinel Robot 🤖</i></p>
        </body>
    </html>
    """
    
    msg.set_content("Check your dashboard for alerts.") # Fallback for non-HTML clients
    msg.add_alternative(html_body, subtype='html')

    # 3. SEND VIA GMAIL SMTP
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER, PASSWORD)
            smtp.send_message(msg)
        print("📨 Email Alert Sent Successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# Test Block
if __name__ == "__main__":
    # Fake data to test the email
    dummy_data = [
        {'Ticker': 'TEST', 'Price': 100, 'Sentiment': 'negative', 'Confidence': 0.95, 'Headline': 'Test Crisis Event'}
    ]
    send_market_alert(dummy_data)