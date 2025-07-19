from flask import Flask, request, jsonify
import smtplib
import dns.resolver
import socket

app = Flask(__name__)

@app.route("/check", methods=["GET"])
def check_email():
    email = request.args.get("email")
    if not email or "@" not in email:
        return jsonify({"status": "error", "reason": "Invalid email format"}), 400

    domain = email.split('@')[1]
    error_log = []

    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_hosts = sorted([(r.preference, str(r.exchange)) for r in mx_records])
    except:
        return jsonify({"status": "error", "reason": "No MX records found"})

    for pref, mx_host in mx_hosts:
        try:
            server = smtplib.SMTP(timeout=10)
            server.connect(mx_host)
            server.helo("example.com")
            server.mail("test@example.com")
            code, msg = server.rcpt(email)
            server.quit()

            if code == 250:
                return jsonify({"status": "valid", "mx": mx_host})
            elif code == 550:
                return jsonify({"status": "invalid", "reason": msg.decode()})
            else:
                return jsonify({
                    "status": "unknown",
                    "smtp_code": code,
                    "smtp_response": msg.decode(),
                    "mx": mx_host
                })
        except Exception as e:
            error_log.append({ "mx": mx_host, "error": str(e) })
            continue

    return jsonify({
        "status": "error",
        "reason": "SMTP check failed on all MX",
        "errors": error_log
    })
