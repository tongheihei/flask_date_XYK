from operator import methodcaller
from os import error
from flask import render_template,flash,url_for,abort,request
from flask_sqlalchemy import Pagination
from werkzeug.utils import redirect
from app.main.forms import EditProfileForm,EditProfileAdminForm,PostForm,CommentForm
from . import main
from ..models import User,Role,Post,Permission,Comment
from .. import db
from flask_login import login_required,current_user
from ..decorators import admin_required,permission_required
@main.route('/',methods=['GET','POST'])
def index():   
    form = PostForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type = int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page = 20, error_out = False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,pagination = pagination)

@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username = username).first_or_404()
    return render_template('user.html',user = user)

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user.get_current_object())
        db.session.commit()
        flash('Your profile has been updated')
        return redirect(url_for('.user',username = current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)

@main.route('/edit-profile/<int:id>',methods=['GET','POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash('评论发表成功')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
          10 + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=10,
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form,
                           comments=comments, pagination=pagination)

@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
        not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash('编辑成功')
        return redirect(url_for('.post', id = post.id))
    
    form.body.data = post.body
    return  render_template('edit_post.html', form = form)
@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=20,
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page = 20,
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)
@main.route('/delete/<int:id>')
def delete_post(id):
    form = PostForm()
    now_post = Post.query.filter_by(id=id).first()
    db.session.delete(now_post)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=20,
        error_out=False)
    posts = pagination.items
    return redirect(url_for('.index'))
@main.route('/editcomment/<int:id>',methods=["GET","POST"])
def editcomment(id):
    comment = Comment.query.get_or_404(id)

    if current_user != comment.author and \
        not current_user.can(Permission.ADMIN):
        abort(403)
    form = CommentForm()
    if form.validate_on_submit():
        comment.body = form.body.data
        db.session.add(comment)
        db.session.commit()
        flash('编辑成功')
        return redirect(url_for('.post', id = comment.post_id))
    
    form.body.data = comment.body
    return  render_template('edit_comment.html', form = form)


