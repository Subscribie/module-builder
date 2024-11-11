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
from subscribie.signals import signal_journey_complete
from subscribie.tasks import task_queue
from .forms import SignupForm
from subscribie.forms import LoginForm
from subscribie.models import Plan, SpamEmailDomain
from subscribie.auth import generate_login_token, login_required
from flask import Blueprint
import json
import uuid
import sqlite3
from subscribie.database import database
import logging

log = logging.getLogger(__name__)

builder = Blueprint("builder", __name__, template_folder="templates")


class Shop(database.Model):
    __tablename__ = "builder_sites"
    __table_args__ = {"extend_existing": True}

    site_url = database.Column(database.String(), primary_key=True)
    email = database.Column(database.String())


def get_client_ip():
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        # The request was sent through a proxy server, so the
        # client IP address is in the X-Forwarded-For header.
        # Get the last IP address in the list.
        client_ip = client_ip.split(",")[-1].strip()
    else:
        # The request was not sent through a proxy server, so
        # the client IP address is in the remote_addr attribute.
        client_ip = request.remote_addr

    return client_ip


@builder.route("/start-building", methods=["GET"])
def start_building():
    form = SignupForm()
    app_config = dict(app.config)
    SUBSCRIBIE_DOMAIN = app_config.get("SUBSCRIBIE_DOMAIN")
    return render_template(
        "start-building.html", form=form, SUBSCRIBIE_DOMAIN=SUBSCRIBIE_DOMAIN
    )


def submit_new_site_build(
    form,
    domain,
    subdomain,
    login_token,
    app_config=None,
    session=None,
    client_ip=None,  # noqa: E501
):
    """Submit a new site build
    Take form submission and build new site from it

    :param form: The metadata for a new shop
    :param domain: The domain for new shop e.g. example.com
    :param login_token: Login token for first time login
    :param subdomain: The subdomain for new shop e.g. abc. Which
    :param app_config: The flask app config type casted to a dict
        when combined with domain, becomes abc.example.com
    :param session: The serialized flask session data
    """
    payload = {}
    payload["version"] = 1
    payload["users"] = [form.email.data]
    payload["password"] = form.password.data
    payload["login_token"] = login_token
    company_name = form.company_name.data
    payload["company"] = {"name": company_name, "logo": "", "start_image": ""}
    # If possible, get country code and send to subscribie deployer
    # Ref: https://github.com/Subscribie/module-builder/issues/33
    payload["country_code"] = session.get("country_code", "US")
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
        plan["description"] = getPlan(form.description.data, index)
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
        log.debug(plan)
        plans.append(plan)
        payload["plans"] = plans
    # Save to json
    json.dumps(payload)
    with open(subdomain + ".json", "w") as fp:
        fp.write(json.dumps(payload))
    deploy_url = app_config.get("JAMLA_DEPLOY_URL")
    deployJamla(subdomain + ".json", deploy_url=deploy_url)

    # Inform
    try:
        token = app_config.get("TELEGRAM_TOKEN", None)
        chat_id = app_config.get("TELEGRAM_CHAT_ID", None)
        new_site_url = f"https://{subdomain}.{domain}"
        if subdomain != "demo":
            task_queue.put(
                lambda: requests.get(
                    f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text=NewShop%20{new_site_url}%20fromIp%20{client_ip}"  # noqa
                )
            )
    except Exception as e:
        log.error(f"Telegram not sent: {e}")

    # Store new site in builder_sites table to allow logging in from subscribie site # noqa: E501
    con = sqlite3.connect(app_config.get("DB_FULL_PATH"))
    email = form.email.data
    query = "INSERT INTO builder_sites (site_url, email) VALUES (?, ?)"
    con.execute(query, (new_site_url, email.lower()))
    con.commit()


@builder.route("/start-building", methods=["POST"])
def save_plans():
    app_config = dict(app.config)
    form = SignupForm()
    domain = app.config.get("SUBSCRIBIE_DOMAIN", ".subscriby.shop")
    subdomain = create_subdomain_string(form.company_name.data)
    form = SignupForm()
    session["email"] = form.email.data

    # Verify that subscriber email address is not
    # a suspected SUSPECTED_SPAM_EMAIL_DOMAINS
    SUSPECTED_SPAM_EMAIL_DOMAINS = [d.domain for d in SpamEmailDomain.query.all()]
    user_email_domain = session["email"].split("@")[1]
    if user_email_domain in SUSPECTED_SPAM_EMAIL_DOMAINS:
        log.error(
            f"SUSPECTED_SPAM_EMAIL_DOMAIN {user_email_domain} "
            "attempted to connect stripe"
        )
        return "<h1>Please contact support before signing-up, thank you.</h1>"

    domain = app.config.get("SUBSCRIBIE_DOMAIN", ".subscriby.shop")
    subdomain = create_subdomain_string(form.company_name.data)

    login_token = generate_login_token()

    session["site-url"] = (
        f'https://{subdomain}.{app.config.get("SUBSCRIBIE_DOMAIN", ".subscriby.shop")}'  # noqa: E501
    )

    # Start new site build in background thread
    app_config = dict(app.config)
    session_dict = dict(session)
    client_ip = get_client_ip()
    task_queue.put(
        lambda: submit_new_site_build(
            form,
            domain,
            subdomain,
            login_token,
            app_config,
            session=session_dict,  # noqa: E501
            client_ip=client_ip,
        )
    )  # noqa: E501

    # Redirect to their site, auto login using login_token
    auto_login_url = f'{session["site-url"]}/auth/login/{login_token}'
    session["login-url"] = auto_login_url
    return auto_login_url


@builder.route("/activate/<sitename>")
def choose_package(sitename=None):
    plans = Plan.query.filter_by(archived=0)
    session["sitename"] = sitename
    return render_template("select-package.html", plans=plans)


def journey_complete_subscriber(sender, **kw):
    log.debug("Journery Complete! Send an email or something..")
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
        log.error(f"Error sending journey_complete_subscriber email: {e}")


@builder.route("/sendJamla")
def deployJamla(filename, deploy_url=None):
    with open(filename) as fp:
        payload = json.loads(fp.read())
        log.debug(f"Deploying new shop: {deploy_url}")
        req = requests.post(deploy_url, json=payload)
        log.debug(f"status_code from {deploy_url} was {req.status_code}")
        req.raise_for_status()
    return "Sent jamla file for deployment"


def create_subdomain_string(company_name=None):
    subdomain = re.sub(r"\W+", "", company_name).lower()
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


@builder.route("/admin/shops", methods=["GET"])
@login_required
def shops():
    """List all shops"""
    shops = Shop.query.all()
    shops = reversed(shops)
    return render_template("shops.html", shops=shops)


def getPlan(container, i, default=None):
    try:
        return container[i]
    except IndexError:
        return default


# Subscribers
signal_journey_complete.connect(journey_complete_subscriber)
