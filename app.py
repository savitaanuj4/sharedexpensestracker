from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from datetime import datetime
from flask_restful import Resource, Api, reqparse, abort, marshal, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView


# Initialize Flask
app = Flask(__name__, static_url_path='/static')
api = Api(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = 'ThisIsSecretKey'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model, UserMixin):
    """ user database to store the information of users """

    # __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String(50), index=True, unique=True, nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    dob = db.Column(db.DateTime, nullable=False)
    address = db.Column(db.String, nullable=False)
    isAdmin = db.Column(db.Integer, nullable=False, default=0)
    password_hash = db.Column(db.String())

    def __init__(self, **kwargs):
        self.first_name = kwargs['first_name']
        self.last_name = kwargs['last_name']
        self.email = kwargs['email']
        self.phone = kwargs['phone']
        self.dob = kwargs['dob']
        self.address = kwargs['address']

    def set_password(self, password):
        """ function to set password hash into the table """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """ function to match password hash """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        """ string representation of current object of user """
        return '<User {}>'.format(self.email)

class Poll(db.Model):
    # __tablename__ = 'Poll'
    pollid = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pollname = db.Column(db.String)
    number_of_persons = db.Column(db.Integer)
    person_names = db.Column(db.String)


class TransactionDetail(db.Model):
    transaction_id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.pollid'))
    payer = db.Column(db.String)
    amount = db.Column(db.Integer)
    purpose = db.Column(db.String(120))


    def __str__(self):
        return f'{self.transaction_id}  {self.payer}'


@app.route('/')
def index():
    """ load homepage"""
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """ function to manage login system """
    if request.method == 'POST':
        users = db.session.query(User).all()
        email = request.form.get('user_email')
        password = request.form.get('user_password')

        for user in users:
            if user.email == email and user.check_password(password):
                if user.isAdmin:
                    return redirect('/admin_dashboard')

                polls = db.session.query(Poll).filter_by(user_id=user.id)

                return render_template('user_dashboard.html', user=user, polls=enumerate(polls))
        else:
            return 'Invalid Password or Username'

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """ function to get info from html template and register the user into the database """
    if request.method == 'GET':
        return render_template('register.html')
    else:
        user_detail = {'first_name': request.form.get('first_name'),
                       'last_name': request.form.get('last_name'),
                       'email': request.form.get('user_email'),
                       'phone': request.form.get('user_phone'),
                       'dob': datetime.strptime(request.form.get('user_dob'), '%Y-%m-%d'),
                       'address': request.form.get('user_address'),
                       # 'password': request.form.get('user_password'),
                       }
        new_user = User(**user_detail)
        new_user.set_password(request.form.get('user_password'))
        db.session.add(new_user)
        db.session.commit()
        return 'user added successfully'

    return render_template('register.html')

@app.route('/new_poll/<int:id>', methods=['GET', 'POST'])
def new_poll(id):
    if request.method == 'POST':

        newpoll = Poll(user_id=id,pollname=request.form['pollname'] , number_of_persons=request.form['number_of_persons'], person_names=request.form['persons'])
        db.session.add(newpoll)
        db.session.commit()
        return 'poll created succesfully!'

    return render_template('new_poll.html')

@app.route('/poll/<int:id>', methods=['GET', 'POST'])
def poll_detail(id):
    if request.method == 'POST':
            print(request.form)

            transaction = TransactionDetail(poll_id=id, payer=request.form['payer'], amount=request.form['amount'], purpose=request.form['purpose'])
            db.session.add(transaction)
            db.session.commit()
            print('transaction added')
            print(transaction)
            return redirect(f'/poll/{id}')
    poll = db.session.query(Poll).filter_by(pollid=id).first()

    persons = [person.strip() for person in poll.person_names.split(',')]
    transactions = db.session.query(TransactionDetail).filter_by(poll_id=id).all()


    return render_template('poll_detail.html', persons=persons, transactions=transactions)


class UserList(Resource):
    """ Api to list all users """

    def get(self):
        users = db.session.query(User).all()

        if len(users) == 0:
            return {}

        result = [{'id': user.id,
                   'first_name': user.first_name,
                   'last_name': user.last_name,
                   'email': user.email,
                   'phone': user.phone,
                   'dob': user.dob.strftime('%Y-%m-%d'),
                   'address': user.address
                   } for user in users]

        return result


class UserDetail(Resource):
    """ Api to list info of one user """

    def get(self):
        id = request.args.get('id')
        users = db.session.query(User).all()

        if len(users) == 0:
            return {}

        result = [{'id': user.id,
                   'first_name': user.first_name,
                   'last_name': user.last_name,
                   'email': user.email,
                   'phone': user.phone,
                   'dob': user.dob.strftime('%Y-%m-%d'),
                   'address': user.address
                   } for user in users if int(id) == user.id]
        return result[0] if len(result) > 0 else {}


class SearchUser(Resource):
    """ Api to search the user based on name and location """

    def get(self):
        name = request.args.get('name').split()
        address = request.args.get('address')
        first_name = name[0]
        last_name = name[1] if len(name) > 1 else ''

        users = db.session.query(User).all()

        if len(users) == 0:
            return []

        result = [{'id': user.id,
                   'first_name': user.first_name,
                   'last_name': user.last_name,
                   'email': user.email,
                   'phone': user.phone,
                   'dob': user.dob.strftime('%Y-%m-%d'),
                   'address': user.address
                   } for user in users if (first_name.lower() == user.first_name.lower() and address.lower() == user.address.lower())]
        return result


@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    """ manages custom admin dashboard """
    users = db.session.query(User).all()

    return render_template('admin_dashboard.html', users=users)


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    """ edits the information of user """
    user = User.query.filter_by(id=id).first()
    if request.method == 'GET':
        return render_template('edit.html', user=user)
    if request.method == 'POST':

        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.email = request.form.get('user_email')
        user.phone = request.form.get('user_phone')
        user.address = request.form.get('user_address')
        user.isAdmin = request.form.get('isAdmin')

        db.session.commit()

        return 'Data Updated Succesfully'


api.add_resource(UserList, "/users")
api.add_resource(UserDetail, '/userDetail')
api.add_resource(SearchUser, '/searchUser')

admin = Admin(app, name='Dashboard')
admin.add_view(ModelView(User, db.session))


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
