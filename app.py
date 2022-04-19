from flask import Flask, url_for, render_template, session, redirect, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from jinja2 import meta
from sqlalchemy import desc, and_
from flask_login import LoginManager, logout_user, current_user, UserMixin, login_user, login_required
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_caching import Cache
import os, sentiment

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:@localhost/circle"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secretley@123'

login_manager = LoginManager(app)
db = SQLAlchemy(app)

app.config['UPLOAD_FOLDER'] = "F:\\flask\\circledub2\\static\\profile_pics"
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'JPG', 'PNG', 'jepg','JEPG'])


##############################################   MODELS   ##########################################

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


likes = db.Table('likes',
                 db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                 db.Column('post_id', db.Integer, db.ForeignKey('post.id'))
                 )

followers = db.Table('follows',
                     db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), nullable=True),
                     db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), nullable=True))

usergroup = db.Table('usergroup',
                     db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                     db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True)
                     )

upvotes = db.Table('upvotes',
                 db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                 db.Column('question_id', db.Integer, db.ForeignKey('question.id'))
                 )


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    fullname = db.Column(db.String(150), nullable=True)
    about = db.Column(db.Text, nullable=True)
    country = db.Column(db.String(55), nullable=True)
    address = db.Column(db.Text, nullable=True)
    twitter = db.Column(db.String(100), nullable=True)
    instagram = db.Column(db.String(100), nullable=True)
    facebook = db.Column(db.String(100), nullable=True)
    linked = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.NUMERIC(13), nullable=True)
    email = db.Column(db.String(55), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    image_file = db.Column(db.String(30), default='default.jpg', nullable=True)
    date_created = db.Column(db.String(25))
    post = db.relationship('Post', backref='author', lazy=True)
    comment = db.relationship('Comment', backref='reply', lazy=True)
    questions = db.relationship('Question', backref='teacher', lazy=True)
    answers = db.relationship('Answer', backref='resp', lazy=True)
    likes = db.relationship('Post', secondary=likes, backref=db.backref('likes', lazy='dynamic'), lazy='dynamic')
    upvotes = db.relationship('Question', secondary=upvotes, backref=db.backref('upvotes', lazy='dynamic'), lazy='dynamic')
    hatepost = db.relationship('hatePost', backref='hate_post', lazy=True)
    hatecomment = db.relationship('hateComment', backref='hater', lazy=True)
    followgroup = db.relationship('Group', secondary=usergroup, backref='followers')
    followed = db.relationship('User', secondary=followers,
                               primaryjoin=(followers.c.follower_id == id),
                               secondaryjoin=(followers.c.followed_id == id),
                               backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')


# POST
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.relationship('Comment', backref='oripost')
    hate_comment = db.relationship('hateComment', backref='receiver', lazy=True)


# Comment
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)


class hatePost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hate_text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class hateComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)



class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    about = db.Column(db.Text, nullable=True)
    questions = db.relationship('Question', backref='discuss', lazy=True)
    answers = db.relationship('Answer', backref='discomment', lazy=True)



class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    answers = db.relationship('Answer', backref='ans', lazy = True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))


# Comment
class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))


####################### END of MODEL ###############################


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db_email = User.query.filter_by(email=email).first()
        db_pword = User.query.filter_by(password=password).first()

        if db_email and db_pword:
            session['logged_in'] = True
            session['username'] = db_email.username
            session['user_id'] = db_email.id
            login_user(db_email)
            return redirect('/dashboard')
        else:
            flash("Login details not matched",'danger')
            return redirect('/login')
    else:
        return render_template('login.html')


@app.route('/profile/<int:id>', methods=["POST", "GET"])
@login_required
def profile(id):
    user = User.query.get(id)
    user_post = Post.query.filter_by(author=user).all()
    return render_template('profile.html', user=user, posts=user_post, datetime=datetime, likes = likes, Comment = Comment)


@app.route('/register', methods=["POST"])
def register():
    uname = request.form['username']
    phone = request.form['phone']
    email = request.form['email']
    password = request.form['password']
    db_username = User.query.filter_by(username=uname).first()
    db_email = User.query.filter_by(email=email).first()
    if db_email:
        flash("email already used", 'danger')
        return redirect('/')
    if db_username:
        flash("username already used",'danger')
        return redirect('/')
    else:
        x = datetime.now()
        creation = str(x.strftime("%d")) + " " + str(x.strftime("%B")) + " " + str(x.strftime("%Y"))

        user = User(username=uname, phone=phone, email=email, password=password, date_created=creation)
        db.session.add(user)
        db.session.commit()
        flash("Register successful please login to continue","success")
        return redirect('/login')


@app.route('/')
def home():
    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    posts = []
    follow_suggestions = User.query.all()[:6]
    follows = current_user.followed.all()
    follows.append(current_user)
    for follow in follows:
        user_posts = Post.query.filter_by(author=follow)
        posts += user_posts
    posts.sort(key=lambda x: x.date_posted, reverse=True)
    if current_user:
        if current_user in follow_suggestions:
            follow_suggestions.remove(current_user)
    return render_template('index.html', suggestion=follow_suggestions, user=current_user, Post_model=Post, likes=likes,
                           User=User, posts=posts, datetime=datetime, Comment = Comment )


@app.route('/new_post', methods=["POST"])
@login_required
def new_post():
    tweet = request.form['tweet']
    log, like = sentiment.train_initiator()
    p = sentiment.naive_bayes_predict(tweet, log, like)
    if p >= 0:
        post = Post(content=tweet, author=current_user)
        db.session.add(post)
        db.session.commit()
        return redirect('/dashboard')
    else:
        hate = hatePost(hate_text=tweet, user_id=current_user.id)
        db.session.add(hate)
        db.session.commit()
        flash("Hate speech detected your post is suspended and send to admin for further review", 'danger')
        return redirect(url_for('dashboard'))


@app.route('/comment/<int:post_id>', methods=["POST"])
@login_required
def comment(post_id):
    retweet = request.form['retweet']
    post = Post.query.get(post_id)

    log, like = sentiment.train_initiator()

    p = sentiment.naive_bayes_predict(retweet, log, like)
    if p >= 0:
        commend = Comment(content=retweet, post_id=post.id, user_id=current_user.id)
        db.session.add(commend)
        db.session.commit()
        return redirect('/dashboard')
    else:
        hatecmd = hateComment(text=retweet, post_id=post.id, user_id=current_user.id)
        db.session.add(hatecmd)
        db.session.commit()
        flash("Hate Comment is detected, your comment is sent to admin for further review", 'danger')
        return redirect(url_for('dashboard'))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/profile/upload/<int:id>', methods=['POST'])
@login_required
def profile_upload(id):
    user = User.query.get_or_404(id)
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('profile', id=user.id))
    file = request.files['file']
    # If empty file
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('profile', id=user.id))
    # If there is a file and it is allowed
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        current_user.image_file = filename
        db.session.commit()
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash(
            f'Succesfully changed profile picture to {filename}', 'success')
        return redirect(url_for('profile', id=user.id))


@app.route('/profile/edit/<int:id>', methods=['POST'])
@login_required
def profile_edit(id):
    user = User.query.get_or_404(id)
    user.fullname = request.form['fullname']
    user.about = request.form['about']
    user.country = request.form['country']
    user.address = request.form['address']
    user.phone = request.form['phone']
    user.twitter = request.form['twitter']
    user.instagram = request.form['instagram']
    user.facebook = request.form['facebook']
    user.linked = request.form['linked']
    db.session.commit()
    flash("successfully updated")
    return redirect(url_for('profile', id=user.id))


@app.route('/profile/password/<int:id>', methods=['POST'])
@login_required
def updatepassword(id):
    user = User.query.get_or_404(id)
    pword = request.form['pword']
    newp = request.form['newpword']
    repword = request.form['repword']
    if (pword == user.password and newp == repword):
        user.password = newp
        db.session.commit()
        flash("password changed successfully")
        return redirect(url_for('profile', id=user.id))
    else:
        flash("Incorrect password")


@app.route('/group')
@login_required
def groups():
    follow_suggestions = User.query.all()[:6]
    follows = current_user.followed.all()
    follows.append(current_user)
    groups = Group.query.all()
    if current_user:
        if current_user in follow_suggestions:
            follow_suggestions.remove(current_user)
    return render_template('group.html', groups=groups, user=current_user, follow_suggestions = follow_suggestions)


@app.route('/group/<int:id>', methods=['POST', 'GET'])
@login_required
def group_page(id):
    group = Group.query.filter_by(id=id).first()
    question = Question.query.filter_by(group_id = group.id).all()
    question.sort(key=lambda x: x.date_posted, reverse=True)
    groups = Group.query.all()[:5]
    if(group in groups):
        groups.remove(group)
    return render_template('group1.html',questions = question, group=group, user=current_user, groups = groups, Answer = Answer,)



@app.route('/follow_group/<int:id>')
@login_required
def follow_group(id):
    user = current_user
    group = Group.query.filter_by(id=id).first()
    user.followgroup.append(group)
    db.session.commit()
    return redirect('/group')


@app.route('/unfollow_group/<int:id>')
@login_required
def unfollow_group(id):
    user = current_user
    group = Group.query.filter_by(id=id).first()
    user.followgroup.remove(group)
    db.session.commit()
    return redirect('/group')


@app.route('/group/group_post/<int:id>', methods=['POST'])
@login_required
def group_post(id):
    ques = request.form['title']
    content = request.form['content']
    group = Group.query.filter_by(id=id).first()
    user = current_user
    question = Question(title=ques, content = content, discuss=group, user_id=user.id)
    db.session.add(question)
    db.session.commit()
    return redirect(url_for('group_page', id=group.id))


@app.route('/group/answer/<int:id>', methods=["POST"])
@login_required
def answers(id):
    ans = request.form['answer']
    question= Question.query.filter_by(id = id).first()
    rep = Answer(content = ans, question_id = question.id, user_id = current_user.id, group_id = question.group_id)
    db.session.add(rep)
    db.session.commit()
    return redirect(url_for('group_page', id=question.group_id))




@app.route('/upvote/<int:id>')
@login_required
def like_question(id):
    question = Question.query.get(id)
    if current_user in question.upvotes.all():
        question.upvotes.remove(current_user)
        db.session.commit()
        return redirect(url_for('group_page',id=question.group_id, _anchor=id))
    else:
        question.upvotes.append(current_user)
        db.session.commit()
        return redirect(url_for('group_page', id=question.group_id, _anchor=id))


@app.route('/like/<int:id>')
@login_required
def like_post(id):
    post = Post.query.get(id)
    if current_user in post.likes.all():
        post.likes.remove(current_user)
        db.session.commit()
        return redirect(url_for('dashboard', _anchor=id))
    else:
        post.likes.append(current_user)
        db.session.commit()
        return redirect(url_for('dashboard', _anchor=id))


@app.route('/follow/<int:id>')
@login_required
def folllow(id):
    user_following = current_user
    user_followed = User.query.filter_by(id=id).first()
    if user_following == user_followed:
        flash("YOu cant follow Yourself")
        return redirect('/dashboard')
    else:
        user_following.followed.append(user_followed)
        db.session.commit()
        return redirect(url_for('dashboard'))


@app.route('/unfollow/<int:id>')
@login_required
def unfollow(id):
    user_unfollowing = current_user
    user_unfollowed = User.query.filter_by(id=id).first()
    if user_unfollowing == user_unfollowed:
        flash("error")
        return redirect(url_for('home'))
    else:
        user_unfollowing.followed.remove(user_unfollowed)
        db.session.commit()
        flash(f"unfollowed{user_unfollowing.username}")
        return redirect(url_for('dashboard'))


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    u_id = current_user.id
    if u_id == 2:
        hatecomment = hateComment.query.all()
        hate = hatePost.query.all()
        return render_template('admin.html', posts=hate, User=User, comments=hatecomment)
    else:
        return jsonify({"sorry": "cannot view the page "})


@app.route('/delete_post/<int:id>')
@login_required
def delete(id):
    det = hatePost.query.get(id)
    db.session.delete(det)
    db.session.commit()
    return redirect('/admin')


@app.route('/post/<int:hate_id>')
@login_required
def post(hate_id):
    hate = hatePost.query.filter_by(id=hate_id).first()
    text = hate.hate_text
    user = hate.user_id
    repost = Post(content=text, user_id=user)
    db.session.add(repost)
    db.session.commit()
    db.session.delete(hate)
    db.session.commit()
    return redirect('/admin')


@app.route('/delete_cmd/<int:id>')
@login_required
def delete_cmd(id):
    det = hateComment.query.get(id)
    db.session.delete(det)
    db.session.commit()
    return redirect('/admin')


@app.route('/recomment/<int:id>')
@login_required
def recomment(id):
    cmd = hateComment.query.filter_by(id=id).first()
    comment = Comment(content=cmd.text, post_id=cmd.post_id, user_id=cmd.user_id)
    db.session.add(comment)
    db.session.commit()
    db.session.delete(cmd)
    db.session.commit()
    return redirect('/admin')


@app.route('/admin/create_group', methods=['POST'])
@login_required
def crete_group():
    gname = request.form['title']
    about = request.form['about']
    group = Group(name=gname, about=about)
    db.session.add(group)
    db.session.commit()
    flash('Successful created groups','success')
    return redirect('/admin')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


if __name__ == '__main__':
    app.run()
