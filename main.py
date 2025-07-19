from flask import Flask, request, jsonify
import smtplib
import dns.resolver
import socket
import time

app = Flask(__name__)

# Dati del mittente reale
MAIL_FROM = "n.vellani@consulenzadedicata.com"
HELO_DOMAIN = "mail.consulenzadedicata.com"

@app.route("/check", methods=["GET"])
def check_email():
    email = request.args.get("email")
    if not email or "@" not in email:
        return jsonify({"status": "error", "reason": "Invalid email format"}), 400

    domain = email.split('@')[1]
    error_log = []

    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_hosts = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in mx_records])
    except Exception as e:
        return jsonify({"status": "error", "reason": f"No MX records found for domain: {domain}", "details": str(e)}), 400

    for pref, mx_host in mx_hosts:
        try:
            server = smtplib.SMTP(mx_host, 25, timeout=10)
            server.set_debuglevel(0)  # Debug a 1 per output dettagliato su console

            # Tentativo EHLO + STARTTLS se supportato
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except:
                pass  # Alcuni server non supportano STARTTLS

            server.helo(HELO_DOMAIN)
            server.mail(MAIL_FROM)
            time.sleep(0.5)  # Delay per evitare 503

            code, msg = server.rcpt(email)
            server.quit()

            msg_decoded = msg.decode() if isinstance(msg, bytes) else str(msg)

            if code == 250:
                return jsonify({"status": "valid", "mx": mx_host, "smtp_code": code, "smtp_response": msg_decoded})
            elif code == 550:
                return jsonify({"status": "invalid", "mx": mx_host, "smtp_code": code, "smtp_response": msg_decoded})
            else:
                return jsonify({
                    "status": "unknown",
                    "mx": mx_host,
                    "smtp_code": code,
                    "smtp_response": msg_decoded
                })

        except Exception as e:
            error_log.append({ "mx": mx_host, "error": str(e) })
            continue

    return jsonify({
        "status": "error",
        "reason": "SMTP check failed on all MX",
        "errors": error_log
    }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
