import os
import re
from flask import (
    render_template,
    session,
    redirect,
    url_for,
    request,
    flash,
    current_app as app,
)
from flask_mail import Mail, Message
import requests
from base64 import urlsafe_b64encode
from subscribie.signals import journey_complete
from .forms import SignupForm
from subscribie.forms import LoginForm
from subscribie.models import Plan
from subscribie.auth import generate_login_token
from flask import Blueprint
import json
import uuid
import sqlite3

builder = Blueprint("builder", __name__, template_folder="templates")


def getConfig(name=None):
    if name is None:
        allConfigs = {}
        for key, value in enumerate(os.environ):
            allConfigs[key] = value
        for key, value in enumerate(app.config):
            allConfigs[key] = value
        return allConfigs
    try:  # Default get from os environment
        print("NOTICE: Attempting to find {} in os environ".format(name))
        return os.environ[name]
    except KeyError:
        pass
    try:  # Fallback get from app config
        print("NOTICE: Attempting to find {} in app config".format(name))
        return app.config[name]
    except KeyError:
        pass

    print("NOTICE: Could not loate value for config: {}".format(name))
    return False


@builder.route("/start-building", methods=["GET"])
def start_building():
    form = SignupForm()
    return render_template("start-building.html", form=form)


@builder.route("/start-building", methods=["POST"])
def save_plans():
    payload = {}
    login_token = generate_login_token()
    form = SignupForm()
    payload["version"] = 1
    payload["users"] = [form.email.data]
    session["email"] = form.email.data
    payload["password"] = form.password.data
    payload["login_token"] = login_token
    company_name = form.company_name.data
    payload["company"] = {"name": company_name, "logo": "", "start_image": ""}
    payload["theme"] = {"name": "jesmond", "static_folder": "./static/"}

    # Custom styles prepare as empty
    payload["theme"]["options"] = {}
    payload["theme"]["options"]["styles"] = []

    # Pages as empty array
    payload["pages"] = []

    plans = []
    for index, plan in enumerate(form.title.data):
        plan = {}
        plan["uuid"] = str(uuid.uuid4())
        plan["title"] = getPlan(form.title.data, index)
        plan["sku"] = getPlan(form.title.data, index)
        if getPlan(form.sell_price.data, index) is None:
            plan["sell_price"] = 0
        else:
            plan["sell_price"] = (
                int(getPlan(form.sell_price.data, index)) * 100
            )  # noqa: E501
        if getPlan(form.interval_amount.data, index) is None:
            plan["interval_amount"] = 0
        else:
            plan["interval_amount"] = (
                getPlan(form.interval_amount.data, index) * 100
            )  # noqa: E501
        plan["interval_unit"] = getPlan(form.interval_unit.data, index)
        plan["description"] = request.form.get("description", "")
        plan["subscription_terms"] = {"minimum_term_months": 12}
        plan["primary_colour"] = "#e73b1a"
        # Plan requirements
        plan["requirements"] = {}
        plan["requirements"]["instant_payment"] = getPlan(
            form.instant_payment.data, index
        )
        plan["requirements"]["subscription"] = getPlan(
            form.subscription.data, index
        )  # noqa: E501
        plan["requirements"]["note_to_seller_required"] = False
        plan["primary_icon"] = {"src": False, "type": False}
        print(plan)
        plans.append(plan)
        payload["plans"] = plans

    subdomain = create_subdomain_string(payload)
    session["site-url"] = "https://" + subdomain.lower() + ".subscriby.shop"

    # Save to json
    json.dumps(payload)
    with open(subdomain + ".json", "w") as fp:
        fp.write(json.dumps(payload))
    deployJamla(subdomain + ".json")

    # Inform
    try:
        token = app.config.get("TELEGRAM_TOKEN", None)
        chat_id = app.config.get("TELEGRAM_CHAT_ID", None)
        new_site_url = session["site-url"]
        requests.get(
            f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text=NewShop%20{new_site_url}"  # noqa
        )
    except Exception as e:
        print(f"Telegram not sent: {e}")

    # Store new site in builder_sites table to allow logging in from subscribie site # noqa: E501
    con = sqlite3.connect(app.config["DB_FULL_PATH"])
    query = "INSERT INTO builder_sites (site_url, email) VALUES (?, ?)"
    con.execute(query, (session["site-url"], session["email"].lower()))
    con.commit()

    from time import sleep

    sleep(3)
    # Redirect to their site, auto login using login_token
    auto_login_url = f'{session["site-url"]}/auth/login/{login_token}'
    return redirect(auto_login_url)


@builder.route("/activate/<sitename>")
def choose_package(sitename=None):
    plans = Plan.query.filter_by(archived=0)
    return render_template("select-package.html", plans=plans)


def journey_complete_subscriber(sender, **kw):
    print("Journery Complete! Send an email or something..")
    try:
        email = kw["email"]
        sender = app.config.get("MAIL_DEFAULT_SENDER", "hello@example.com")
        login_url = session["login-url"]
        msg = Message(
            subject="Subscription Website Activated",
            body=login_url,
            sender=sender,
            recipients=[email],
        )
        # Load builder module env
        mail = Mail(app)
        mail.send(msg)
    except Exception as e:
        print("Error sending journey_complete_subscriber email")
        print(e)
        pass


@builder.route("/sendJamla")
def deployJamla(filename):
    url = getConfig("JAMLA_DEPLOY_URL")
    with open(filename) as fp:
        payload = json.loads(fp.read())
        r = requests.post(url, json=payload)
        session["login-url"] = r.text
    return "Sent jamla file for deployment"


def create_subdomain_string(jamla=None):
    if jamla is None:
        subdomain = urlsafe_b64encode(os.urandom(5)).replace("=", "")
    else:
        subdomain = re.sub(r"\W+", "", jamla["company"]["name"])
    return subdomain


@builder.route("/shop-owner-login/", methods=["GET", "POST"])
def shop_owner_login():
    """Locate and redirect shop owner to their shop url

    Shops are hosted on their own instance, with their own database
    so we must direct them to their shop, by:

    - Searching for their shop url, via email
    - Redirect user to their shop's login page
    """
    if request.method == "POST":
        email = request.form["email"].lower()
        con = sqlite3.connect(app.config["DB_FULL_PATH"])
        cur = con.cursor()
        query = "SELECT site_url FROM builder_sites WHERE email = ?"
        cur.execute(query, (email,))
        result = cur.fetchone()
        if result is None:
            flash("Site not found, please use the email used during sign-up")
            return redirect(url_for("builder.shop_owner_login"))
        else:
            # Redirect user to their shop url
            site_url = result[0]
            destination = site_url + "/auth/login"
            return redirect(destination)

    if request.method == "GET":
        form = LoginForm()
        return render_template("login.html", form=form)


def getPlan(container, i, default=None):
    try:
        return container[i]
    except IndexError:
        return default


# Subscribers
journey_complete.connect(journey_complete_subscriber)
