import json
import math
import re
from functools import wraps
from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from db import get_db

verify_bp = Blueprint("verify", __name__)


def customer_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("main.login"))
        if session.get("role") not in ("customer", "admin"):
            flash("Customer access required.", "danger")
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)

    return wrapped


def _validate_ph_phone(phone):
    cleaned = re.sub(r"[\s\-()]", "", phone or "")
    if re.match(r"^(09\d{9}|\+639\d{9})$", cleaned):
        return True, cleaned
    return False, cleaned


def _validate_name(name, label="Name"):
    if not name or len(name) < 2:
        return f"{label} must be at least 2 characters."
    if len(name) > 60:
        return f"{label} is too long (maximum 60 characters)."
    if not re.match(r"^[A-Za-z0-9\s.,'\-&]+$", name):
        return f"{label} contains invalid characters."
    return None


def _validate_id_number(id_number):
    if not id_number or len(id_number) < 4 or len(id_number) > 40:
        return "ID Number must be between 4 and 40 characters."
    if not re.match(r"^[A-Za-z0-9\-\s]+$", id_number):
        return "ID Number contains invalid characters."
    return None


# -------------------------------------------------------------------------
# Unified Single-URL 3-Step Verification Wizard (/customer/verification)
# Prevents URL-skipping to Step 2 or Step 3
# -------------------------------------------------------------------------
@verify_bp.route("/customer/verification/step1", methods=["GET", "POST"])
@verify_bp.route("/customer/verification/step2", methods=["GET", "POST"])
@verify_bp.route("/customer/verification/step3", methods=["GET", "POST"])
@customer_required
def redirect_old_steps():
    return redirect(url_for("verify.wizard"))


@verify_bp.route("/customer/verification", methods=["GET", "POST"])
@customer_required
def wizard():

    user_id = session.get("user_id")
    conn = get_db()
    customer = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    current_step = session.get("verify_step", 1)
    if current_step not in (1, 2, 3):
        current_step = 1

    if request.method == "POST":
        nav = request.form.get("nav", "")

        # Handle Back navigation without changing URL
        if nav == "back_to_1":
            session["verify_step"] = 1
            conn.close()
            return redirect(url_for("verify.wizard"))
        if nav == "back_to_2":
            if session.get("verify_step1") and customer["face_descriptor"]:
                session["verify_step"] = 2
            else:
                session["verify_step"] = 1
            conn.close()
            return redirect(url_for("verify.wizard"))

        # Handle Step 1 Submission: Facial Recognition + ID OCR
        if current_step == 1 or request.form.get("wizard_step") == "1":
            id_type = request.form.get("id_type", "").strip()
            id_number = request.form.get("id_number", "").strip()
            id_ocr_name = request.form.get("id_ocr_name", "").strip()
            id_ocr_text = request.form.get("id_ocr_text", "").strip()
            ocr_address = request.form.get("ocr_address", "").strip()

            # 1. Enforce Face Scan
            if not customer["face_descriptor"]:
                conn.close()
                flash("Facial scan is required. Please capture and enroll your Face ID first.", "warning")
                return render_template("customer/verify_step1.html", customer=customer)

            # 2. Enforce ID OCR Scan (must have actual OCR text extracted from ID image)
            if not id_ocr_text or len(id_ocr_text) < 10:
                conn.close()
                flash("Government ID OCR scan is required. Please upload your ID photo and click 'Scan ID with OCR'.", "warning")
                return render_template("customer/verify_step1.html", customer=customer)

            # 3. Validate ID Fields & verify extracted ID Number matches OCR text
            name_err = _validate_name(id_ocr_name, "Full Name on ID")
            id_err = _validate_id_number(id_number)
            if not id_type or name_err or id_err:
                conn.close()
                flash(name_err or id_err or "Please select a valid ID Type.", "warning")
                return render_template("customer/verify_step1.html", customer=customer)

            clean_id = re.sub(r"[^A-Za-z0-9]", "", id_number).lower()
            clean_ocr = re.sub(r"[^A-Za-z0-9]", "", id_ocr_text).lower()
            if clean_id not in clean_ocr:
                conn.close()
                flash("ID Number does not match the scanned Government ID text. Please re-scan your ID.", "danger")
                return render_template("customer/verify_step1.html", customer=customer)

            session["verify_step1"] = {
                "id_type": id_type,
                "id_number": id_number,
                "id_ocr_name": id_ocr_name,
                "id_ocr_text": id_ocr_text,
                "ocr_address": ocr_address[:200],
            }
            conn.execute(
                "UPDATE users SET id_type = ?, id_number = ?, id_ocr_name = ?, id_ocr_text = ? WHERE id = ?",
                (id_type, id_number, id_ocr_name, id_ocr_text, user_id),
            )
            conn.commit()
            conn.close()
            session["verify_step"] = 2
            return redirect(url_for("verify.wizard"))

        # Handle Step 2 Submission: Basic Information
        if current_step == 2 and request.form.get("wizard_step") == "2":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            birthdate = request.form.get("birthdate", "").strip()
            gender = request.form.get("gender", "").strip()
            address = request.form.get("address", "").strip()

            step2_draft = {
                "name": name, "email": email, "phone": phone,
                "birthdate": birthdate, "gender": gender, "address": address,
            }

            name_err = _validate_name(name, "Full / Company Name")
            if name_err:
                conn.close()
                flash(name_err, "warning")
                return render_template("customer/verify_step2.html", customer=customer, step1_data=session.get("verify_step1", {}), step2_data=step2_draft)

            if not email or len(email) > 100 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                conn.close()
                flash("Please enter a valid email address (max 100 characters).", "danger")
                return render_template("customer/verify_step2.html", customer=customer, step1_data=session.get("verify_step1", {}), step2_data=step2_draft)

            is_phone_ok, clean_phone = _validate_ph_phone(phone)
            if not is_phone_ok:
                conn.close()
                flash("Please enter a valid Philippine mobile number (e.g. 09171234567).", "danger")
                return render_template("customer/verify_step2.html", customer=customer, step1_data=session.get("verify_step1", {}), step2_data=step2_draft)

            if not birthdate or not re.match(r"^\d{4}-\d{2}-\d{2}$", birthdate):
                conn.close()
                flash("Please enter a valid birthdate.", "warning")
                return render_template("customer/verify_step2.html", customer=customer, step1_data=session.get("verify_step1", {}), step2_data=step2_draft)

            if not address or len(address) < 10 or len(address) > 200:
                conn.close()
                flash("Delivery address must be between 10 and 200 characters.", "warning")
                return render_template("customer/verify_step2.html", customer=customer, step1_data=session.get("verify_step1", {}), step2_data=step2_draft)

            dup = conn.execute(
                "SELECT id FROM users WHERE LOWER(email) = ? AND id != ?",
                (email, user_id),
            ).fetchone()
            if dup:
                conn.close()
                flash("That email address is already used by another account.", "danger")
                return render_template("customer/verify_step2.html", customer=customer, step1_data=session.get("verify_step1", {}), step2_data=step2_draft)

            session["verify_step2"] = {
                "name": name,
                "email": email,
                "phone": clean_phone,
                "birthdate": birthdate,
                "gender": gender or "Prefer not to say",
                "address": address,
            }
            conn.close()
            session["verify_step"] = 3
            return redirect(url_for("verify.wizard"))

        # Handle Step 3 Submission: Confirm 1 & 2
        if current_step == 3 and request.form.get("wizard_step") == "3":
            step1_data = session.get("verify_step1")
            step2_data = session.get("verify_step2")

            if not customer["face_descriptor"] or not step1_data or not step2_data:
                conn.close()
                session["verify_step"] = 1
                flash("Verification session incomplete. Please complete Step 1 and Step 2.", "warning")
                return redirect(url_for("verify.wizard"))

            conn.execute(
                """
                UPDATE users
                SET name = ?, email = ?, phone = ?, birthdate = ?, gender = ?, address = ?,
                    id_type = ?, id_number = ?, id_ocr_name = ?, id_ocr_text = ?,
                    id_verified = 1, id_verified_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (
                    step2_data["name"],
                    step2_data["email"],
                    step2_data["phone"],
                    step2_data.get("birthdate", ""),
                    step2_data.get("gender", ""),
                    step2_data["address"],
                    step1_data["id_type"],
                    step1_data["id_number"],
                    step1_data["id_ocr_name"],
                    step1_data.get("id_ocr_text", ""),
                    user_id,
                ),
            )
            conn.commit()
            conn.close()

            session["user_name"] = step2_data["name"]
            session["user_email"] = step2_data["email"]
            session.pop("verify_step", None)
            session.pop("verify_step1", None)
            session.pop("verify_step2", None)

            flash("Verification and basic information confirmed and saved!", "success")
            return redirect(url_for("main.customer_settings"))

    # Server-side guard on GET: enforce prerequisites before rendering Step 2 or Step 3
    if current_step == 3 and (not customer["face_descriptor"] or not session.get("verify_step1") or not session.get("verify_step2")):
        current_step = 2 if (customer["face_descriptor"] and session.get("verify_step1")) else 1
        session["verify_step"] = current_step

    if current_step == 2 and (not customer["face_descriptor"] or not session.get("verify_step1")):
        current_step = 1
        session["verify_step"] = 1

    conn.close()
    if current_step == 2:
        return render_template(
            "customer/verify_step2.html",
            customer=customer,
            step1_data=session.get("verify_step1", {}),
            step2_data=session.get("verify_step2", {}),
        )
    if current_step == 3:
        return render_template(
            "customer/verify_step3.html",
            customer=customer,
            step1_data=session.get("verify_step1", {}),
            step2_data=session.get("verify_step2", {}),
        )
    return render_template("customer/verify_step1.html", customer=customer)


# -------------------------------------------------------------------------
# Facial Recognition APIs (face-api.js 128-d descriptor)
# -------------------------------------------------------------------------
@verify_bp.route("/api/customer/face/enroll", methods=["POST"])
@customer_required
def api_face_enroll():
    data = request.get_json(silent=True) or {}
    descriptor = data.get("descriptor")
    if not isinstance(descriptor, list) or len(descriptor) != 128:
        return jsonify({"ok": False, "error": "Invalid 128-d face descriptor."}), 400
    try:
        clean_desc = [float(x) for x in descriptor]
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Descriptor must be numeric."}), 400

    user_id = session.get("user_id")
    conn = get_db()
    conn.execute(
        "UPDATE users SET face_descriptor = ?, face_enrolled_at = datetime('now', 'localtime') WHERE id = ?",
        (json.dumps(clean_desc), user_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "Face ID enrolled successfully!"})


@verify_bp.route("/api/customer/face/remove", methods=["POST"])
@customer_required
def api_face_remove():
    user_id = session.get("user_id")
    conn = get_db()
    conn.execute(
        "UPDATE users SET face_descriptor = NULL, face_enrolled_at = NULL WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
    session["verify_step"] = 1
    return jsonify({"ok": True, "message": "Face ID removed."})


@verify_bp.route("/api/auth/face-login", methods=["POST"])
def api_face_login():
    data = request.get_json(silent=True) or {}
    descriptor = data.get("descriptor")
    email_hint = (data.get("email") or "").strip().lower()

    if not isinstance(descriptor, list) or len(descriptor) != 128:
        return jsonify({"ok": False, "error": "Invalid face descriptor."}), 400
    try:
        probe = [float(x) for x in descriptor]
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid face descriptor format."}), 400

    conn = get_db()
    if email_hint:
        candidates = conn.execute(
            "SELECT * FROM users WHERE role = 'customer' AND is_active = 1 AND face_descriptor IS NOT NULL AND LOWER(email) = ?",
            (email_hint,),
        ).fetchall()
    else:
        candidates = conn.execute(
            "SELECT * FROM users WHERE role = 'customer' AND is_active = 1 AND face_descriptor IS NOT NULL"
        ).fetchall()

    best_user = None
    best_dist = 999.0
    for u in candidates:
        try:
            stored = json.loads(u["face_descriptor"])
            if len(stored) != 128:
                continue
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(probe, stored)))
            if dist < best_dist:
                best_dist = dist
                best_user = u
        except Exception:
            continue

    if best_user and best_dist <= 0.52:
        session["user_id"] = best_user["id"]
        session["role"] = best_user["role"]
        session["user_name"] = best_user["name"]
        session["user_email"] = best_user["email"]
        conn.close()
        return jsonify({
            "ok": True,
            "name": best_user["name"],
            "distance": round(best_dist, 4),
            "redirect": url_for("main.customer_dashboard"),
        })

    conn.close()
    return jsonify({
        "ok": False,
        "error": "Face not recognized. Please enroll Face ID in Customer Verification first.",
    }), 401
