import os
from datetime import datetime

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
database_url = os.getenv("DATABASE_URL", "sqlite:///ournews.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

ALLOWED_UPLOADS = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "mov", "webm"}

POST_CATEGORIES = [
    "Local News",
    "Community Event",
    "Lost Pet",
    "Council Update",
    "School Activity",
    "Sports Result",
    "Business Announcement",
    "Historical Story",
    "Photo Story",
    "Other",
]

WEATHER_COORDS = {
    "katoomba": {"lat": -33.7124, "lon": 150.3119},
    "leura": {"lat": -33.7127, "lon": 150.3301},
    "wagga-wagga": {"lat": -35.1082, "lon": 147.3598},
    "healesville": {"lat": -37.6534, "lon": 145.5171},
}


def is_allowed_upload(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_UPLOADS


class State(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    regions = db.relationship("Region", backref="state", lazy=True)


class Region(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey("state.id"), nullable=False)
    towns = db.relationship("Town", backref="region", lazy=True)


class Town(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(280), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey("region.id"), nullable=False)
    posts = db.relationship("Post", backref="town", lazy=True)
    events = db.relationship("Event", backref="town", lazy=True)
    organizations = db.relationship("Organization", backref="town", lazy=True)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    bio = db.Column(db.String(280), nullable=False, default="Community contributor")
    town_id = db.Column(db.Integer, db.ForeignKey("town.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    town = db.relationship("Town", backref="contributors", foreign_keys=[town_id])

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    summary = db.Column(db.String(260), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False, default="Local News")
    status = db.Column(db.String(32), nullable=False, default="pending")
    image_url = db.Column(db.String(300), nullable=True)
    video_url = db.Column(db.String(300), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    town_id = db.Column(db.Integer, db.ForeignKey("town.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    author = db.relationship("User", backref="posts", foreign_keys=[author_id])


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    starts_on = db.Column(db.DateTime, nullable=False)
    details = db.Column(db.String(360), nullable=False)
    town_id = db.Column(db.Integer, db.ForeignKey("town.id"), nullable=False)


class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    kind = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(360), nullable=False)
    website = db.Column(db.String(260), nullable=True)
    town_id = db.Column(db.Integer, db.ForeignKey("town.id"), nullable=False)


class TownApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    town_name = db.Column(db.String(120), nullable=False)
    region_name = db.Column(db.String(120), nullable=False)
    state_name = db.Column(db.String(120), nullable=False)
    applicant_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False)
    notes = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def seed_platform_if_empty() -> None:
    if db.session.query(func.count(State.id)).scalar() == 0:
        nsw = State(name="New South Wales", slug="new-south-wales")
        vic = State(name="Victoria", slug="victoria")

        blue_mountains = Region(name="Blue Mountains", slug="blue-mountains", state=nsw)
        riverina = Region(name="Riverina", slug="riverina", state=nsw)
        yarra_ranges = Region(name="Yarra Ranges", slug="yarra-ranges", state=vic)

        katoomba = Town(
            name="Katoomba",
            slug="katoomba",
            region=blue_mountains,
            description="Local stories, events and updates for Katoomba residents.",
        )
        leura = Town(
            name="Leura",
            slug="leura",
            region=blue_mountains,
            description="Community updates and local happenings in Leura.",
        )
        wagga = Town(
            name="Wagga Wagga",
            slug="wagga-wagga",
            region=riverina,
            description="News and announcements from Wagga Wagga and surrounds.",
        )
        healesville = Town(
            name="Healesville",
            slug="healesville",
            region=yarra_ranges,
            description="Stories and events from the Healesville community.",
        )

        db.session.add_all([nsw, vic, blue_mountains, riverina, yarra_ranges, katoomba, leura, wagga, healesville])
        db.session.commit()

    if db.session.query(func.count(Post.id)).scalar() > 0:
        return

    katoomba = Town.query.filter_by(slug="katoomba").first()
    leura = Town.query.filter_by(slug="leura").first()
    healesville = Town.query.filter_by(slug="healesville").first()

    if not katoomba or not leura or not healesville:
        return

    starter_posts = [
        Post(
            title="Katoomba Winter Festival Schedule Released",
            slug="katoomba-winter-festival-schedule",
            summary="The town unveils its week-long program of markets, music, and evening events.",
            content=(
                "Organizers confirmed that local artists, schools and businesses will participate "
                "in this year's festival. Residents can now access program maps and event times online."
            ),
            category="Community Event",
            status="published",
            town_id=katoomba.id,
        ),
        Post(
            title="Leura Primary Launches New Robotics Club",
            slug="leura-primary-robotics-club",
            summary="Students and parents gather for the opening session after school on Thursday.",
            content=(
                "The school says the club is open to all year levels and aims to build practical "
                "skills through hands-on challenges, coding basics, and team projects."
            ),
            category="School Activity",
            status="published",
            town_id=leura.id,
        ),
        Post(
            title="Healesville Community Reports Missing Kelpie",
            slug="healesville-missing-kelpie",
            summary="Residents are helping search teams after a dog went missing near the reserve.",
            content=(
                "The family has shared a contact number and recent photo. Local groups are coordinating "
                "search areas and encouraging residents to report sightings promptly."
            ),
            category="Lost Pet",
            status="published",
            town_id=healesville.id,
        ),
    ]
    db.session.add_all(starter_posts)

    starter_events = [
        Event(
            title="Katoomba Council Q&A Night",
            starts_on=datetime(2026, 7, 2, 18, 30),
            details="Residents can ask questions on transport and town planning.",
            town_id=katoomba.id,
        ),
        Event(
            title="Leura Community Garden Working Bee",
            starts_on=datetime(2026, 6, 14, 9, 0),
            details="Bring gloves, hats, and water. New volunteers are welcome.",
            town_id=leura.id,
        ),
    ]
    db.session.add_all(starter_events)

    starter_organizations = [
        Organization(
            name="Blue Mountains Chamber of Commerce",
            kind="Business Association",
            description="Supporting local business networking and growth in the mountains.",
            website="https://example.org/chamber",
            town_id=katoomba.id,
        ),
        Organization(
            name="Leura Community Arts",
            kind="Community Group",
            description="Volunteer-led arts events, classes and exhibitions.",
            website="https://example.org/arts",
            town_id=leura.id,
        ),
    ]
    db.session.add_all(starter_organizations)
    db.session.commit()


def ensure_admin_user() -> None:
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    admin = User.query.filter_by(username=admin_username).first()
    if admin:
        return

    default_town = Town.query.first()
    admin = User(username=admin_username, is_admin=True)
    admin.email = f"{admin_username}@ournews.local"
    admin.town_id = default_town.id if default_town else None
    admin.bio = "Platform administrator"
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.commit()


@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    seed_platform_if_empty()
    ensure_admin_user()
    print("Database initialized. Admin user is ready.")


@app.before_request
def ensure_tables():
    db.create_all()
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    seed_platform_if_empty()
    ensure_admin_user()


@app.context_processor
def inject_globals():
    breaking_posts = (
        Post.query.filter_by(status="published")
        .order_by(Post.created_at.desc())
        .limit(8)
        .all()
    )
    return {
        "all_states": State.query.order_by(State.name.asc()).all(),
        "post_categories": POST_CATEGORIES,
        "breaking_posts": breaking_posts,
    }


@app.route("/")
def home():
    posts = Post.query.filter_by(status="published").order_by(Post.created_at.desc()).limit(4).all()
    towns = Town.query.order_by(Town.name.asc()).limit(8).all()
    featured_town = towns[0] if towns else None
    featured_weather = WEATHER_COORDS.get(featured_town.slug) if featured_town else None
    return render_template(
        "index.html",
        posts=posts,
        towns=towns,
        featured_town=featured_town,
        featured_weather=featured_weather,
    )


@app.route("/australia")
def australia():
    states = State.query.order_by(State.name.asc()).all()
    return render_template("australia.html", states=states)


@app.route("/state/<slug>")
def state_page(slug: str):
    state = State.query.filter_by(slug=slug).first()
    if not state:
        abort(404)
    return render_template("state.html", state=state)


@app.route("/region/<slug>")
def region_page(slug: str):
    region = Region.query.filter_by(slug=slug).first()
    if not region:
        abort(404)
    return render_template("region.html", region=region)


@app.route("/town/<slug>")
def town_page(slug: str):
    town = Town.query.filter_by(slug=slug).first()
    if not town:
        abort(404)
    posts = Post.query.filter_by(town_id=town.id, status="published").order_by(Post.created_at.desc()).all()
    events = Event.query.filter_by(town_id=town.id).order_by(Event.starts_on.asc()).all()
    organizations = Organization.query.filter_by(town_id=town.id).order_by(Organization.name.asc()).all()
    return render_template(
        "town.html",
        town=town,
        posts=posts,
        events=events,
        organizations=organizations,
        weather_coords=WEATHER_COORDS.get(town.slug),
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            flash("Please fill out all contact fields.", "error")
        else:
            flash("Thanks. Your message has been received.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/help-centre")
def help_centre():
    return render_template("help_centre.html")


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")


@app.route("/news")
def news():
    posts = Post.query.filter_by(status="published").order_by(Post.created_at.desc()).all()
    return render_template("news.html", posts=posts)


@app.route("/archive")
def archive():
    query_text = request.args.get("q", "").strip()
    town_slug = request.args.get("town", "").strip()
    category = request.args.get("category", "").strip()

    posts_query = Post.query.filter_by(status="published")
    if query_text:
        wildcard = f"%{query_text}%"
        posts_query = posts_query.filter(
            or_(
                Post.title.ilike(wildcard),
                Post.summary.ilike(wildcard),
                Post.content.ilike(wildcard),
            )
        )

    selected_town = None
    if town_slug:
        selected_town = Town.query.filter_by(slug=town_slug).first()
        if selected_town:
            posts_query = posts_query.filter_by(town_id=selected_town.id)

    if category and category in POST_CATEGORIES:
        posts_query = posts_query.filter_by(category=category)

    posts = posts_query.order_by(Post.created_at.desc()).all()
    towns = Town.query.order_by(Town.name.asc()).all()
    return render_template(
        "archive.html",
        posts=posts,
        towns=towns,
        selected_town=selected_town,
        selected_category=category,
        query_text=query_text,
    )


@app.route("/news/<slug>")
def article(slug: str):
    post = Post.query.filter_by(slug=slug, status="published").first()
    if not post:
        abort(404)
    return render_template("article.html", post=post)


@app.route("/register", methods=["GET", "POST"])
def register():
    towns = Town.query.order_by(Town.name.asc()).all()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        bio = request.form.get("bio", "").strip()
        town_id = request.form.get("town_id", "").strip()

        if not username or not email or not password:
            flash("Username, email and password are required.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Username is already taken.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Email is already registered.", "error")
        else:
            user = User(
                username=username,
                email=email,
                bio=bio or "Community contributor",
                town_id=int(town_id) if town_id.isdigit() else None,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome to OurNews Australia.", "success")
            return redirect(url_for("home"))

    return render_template("register.html", towns=towns)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Invalid username or password.", "error")
        else:
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    return redirect(url_for("login"))


@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/profile/<username>")
def profile(username: str):
    user = User.query.filter_by(username=username).first()
    if not user:
        abort(404)
    posts = (
        Post.query.filter_by(author_id=user.id, status="published")
        .order_by(Post.created_at.desc())
        .all()
    )
    return render_template("profile.html", profile_user=user, posts=posts)


@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit_post():
    towns = Town.query.order_by(Town.name.asc()).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip().lower()
        summary = request.form.get("summary", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", "Local News").strip()
        image_url = request.form.get("image_url", "").strip()
        video_url = request.form.get("video_url", "").strip()
        town_id = request.form.get("town_id", "").strip()
        media_file = request.files.get("media_file")

        if not title or not slug or not summary or not content or not town_id:
            flash("Please complete all required fields.", "error")
        elif Post.query.filter_by(slug=slug).first():
            flash("Slug already exists. Choose another.", "error")
        elif category not in POST_CATEGORIES:
            flash("Choose a valid category.", "error")
        else:
            if media_file and media_file.filename:
                if not is_allowed_upload(media_file.filename):
                    flash("Unsupported upload type. Use image or video files.", "error")
                    return render_template("submit_post.html", towns=towns)

                safe_name = secure_filename(media_file.filename)
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                filename = f"{timestamp}_{safe_name}"
                media_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                media_file.save(media_path)

                ext = filename.rsplit(".", 1)[1].lower()
                relative_path = f"uploads/{filename}"
                if ext in {"mp4", "mov", "webm"}:
                    video_url = relative_path
                else:
                    image_url = relative_path

            post = Post(
                title=title,
                slug=slug,
                summary=summary,
                content=content,
                category=category,
                image_url=image_url or None,
                video_url=video_url or None,
                town_id=int(town_id),
                author_id=current_user.id,
                status="published" if current_user.is_admin else "pending",
            )
            db.session.add(post)
            db.session.commit()
            if current_user.is_admin:
                flash("Post published.", "success")
            else:
                flash("Post submitted for moderation.", "success")
            return redirect(url_for("town_page", slug=post.town.slug))

    return render_template("submit_post.html", towns=towns)


@app.route("/expansion/apply", methods=["GET", "POST"])
def expansion_apply():
    if request.method == "POST":
        town_name = request.form.get("town_name", "").strip()
        region_name = request.form.get("region_name", "").strip()
        state_name = request.form.get("state_name", "").strip()
        applicant_name = request.form.get("applicant_name", "").strip()
        email = request.form.get("email", "").strip()
        notes = request.form.get("notes", "").strip()

        if not all([town_name, region_name, state_name, applicant_name, email, notes]):
            flash("All application fields are required.", "error")
        else:
            application = TownApplication(
                town_name=town_name,
                region_name=region_name,
                state_name=state_name,
                applicant_name=applicant_name,
                email=email,
                notes=notes,
            )
            db.session.add(application)
            db.session.commit()
            flash("Application submitted. Our team will review it.", "success")
            return redirect(url_for("home"))

    return render_template("expansion_apply.html")


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)

    if request.method == "POST":
        action = request.form.get("action", "")
        post_id = request.form.get("post_id", "")
        app_id = request.form.get("application_id", "")

        if action in ["publish", "reject"] and post_id.isdigit():
            post = db.session.get(Post, int(post_id))
            if post:
                post.status = "published" if action == "publish" else "rejected"
                db.session.commit()
                flash("Moderation action applied.", "success")
        elif action in ["approve-town", "decline-town"] and app_id.isdigit():
            application = db.session.get(TownApplication, int(app_id))
            if application:
                application.status = "approved" if action == "approve-town" else "declined"
                db.session.commit()
                flash("Town request updated.", "success")

        return redirect(url_for("admin_dashboard"))

    pending_posts = Post.query.filter_by(status="pending").order_by(Post.created_at.asc()).all()
    pending_applications = TownApplication.query.filter_by(status="pending").order_by(TownApplication.created_at.asc()).all()
    latest_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()

    return render_template(
        "admin_dashboard.html",
        pending_posts=pending_posts,
        pending_applications=pending_applications,
        posts=latest_posts,
    )


if __name__ == "__main__":
    app.run(debug=True)
