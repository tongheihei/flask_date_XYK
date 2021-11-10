from operator import methodcaller
from os import error
from flask import render_template,flash,url_for,abort,request,current_app,send_from_directory
from flask_sqlalchemy import Pagination
from werkzeug.utils import redirect
from app.main.forms import EditProfileForm,EditProfileAdminForm,PostForm,CommentForm,NewAlbumForm,AddPhotoForm
from . import main
from ..models import User,Role,Post,Permission,Comment,Album,Photo
from .. import db,photos
from flask_login import login_required,current_user
from ..decorators import admin_required,permission_required
import time
import hashlib
import PIL
import os
from PIL import Image
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
@main.route('/deletecomment/<int:id>')
def deletecomment(id):
    now_comment = Comment.query.filter_by(id=id).first()
    goid = now_comment.post_id
    db.session.delete(now_comment)
    db.session.commit()
    return redirect(url_for('.post', id = goid))

@main.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOADED_PHOTOS_DEST'],
                               filename)

# add different suffix for image
img_suffix = {
    300: '_t',  # thumbnail
    800: '_s'  # show
}
def image_resize(image, base_width):
    #: create thumbnail
    filename, ext = os.path.splitext(image)
    img = Image.open(photos.path(image))
    if img.size[0] <= base_width:
        return photos.url(image)
    w_percent = (base_width / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)
    img.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename + img_suffix[base_width] + ext))
    return url_for('.uploaded_file', filename=filename + img_suffix[base_width] + ext)

def save_image(files):
    print(1)
    photo_amount = len(files)
    if photo_amount > 50:
        flash(u'抱歉，测试阶段每次上传不超过50张！', 'warning')
        return redirect(url_for('.new_album'))
    images = []
    for img in files:
        filename = hashlib.md5((current_user.username + str(time.time())).encode('UTF-8')).hexdigest()[:10]
        image = photos.save(img, name=filename + '.')
        file_url = photos.url(image)
        url_s = image_resize(image, 800)
        url_t = image_resize(image, 300)
        images.append((file_url, url_s, url_t))
    return images
@main.route('/new-album', methods=['GET', 'POST'])
@login_required
def new_album():
    print(1111111111111)
    form = NewAlbumForm()
    if form.validate_on_submit(): # current_user.can(Permission.CREATE_ALBUMS)
        if request.method == 'POST' and 'photo' in request.files:
            print(1)
            images = save_image(request.files.getlist('photo'))
        print(request.files)
        title = form.title.data
        about = form.about.data
        author = current_user._get_current_object()
        album = Album(title=title, about=about,cover=images[0][2]
                     ,author=author)
        db.session.add(album)
        for url in images:
            photo = Photo(url=url[0], url_s=url[1], url_t=url[2],
                          album=album, author=current_user._get_current_object())
            db.session.add(photo)
        db.session.commit()
        flash(u'相册创建成功！', 'success')
        return redirect(url_for('.index'))
    

    return render_template('new_album.html', form=form)
@main.route('/add-photo/<int:id>', methods=['GET', 'POST'])
@login_required
def add_photo(id):
    album = Album.query.get_or_404(id)
    form = AddPhotoForm()
    if form.validate_on_submit(): # current_user.can(Permission.CREATE_ALBUMS)
        if request.method == 'POST' and 'photo' in request.files:
            images = save_image(request.files.getlist('photo'))

            for url in images:
                photo = Photo(url=url[0], url_s=url[1], url_t=url[2],
                              album=album, author=current_user._get_current_object())
                db.session.add(photo)
            db.session.commit()
        flash(u'图片添加成功！', 'success')
        return redirect(url_for('.index', id=album.id))
    return render_template('add_photo.html', form=form, album=album)


@main.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    return render_template('upload.html')


@main.route('/upload-add', methods=['GET', 'POST'])
@login_required
def upload_add():
    id = request.form.get('album')
    return redirect(url_for('.add_photo', id=id))

@main.route('/photogragh', methods=['GET', 'POST'])
@login_required
def albums():
    page = request.args.get('page', 1, type=int)
    pagination = Album.query.order_by(Album.timestamp.desc()).paginate(
        page, per_page = 1, error_out = False)

    albums = pagination.items
    for album in albums:
        print(album.cover)

    return render_template('albums.html', user=current_user, albums=albums,pagination=pagination)