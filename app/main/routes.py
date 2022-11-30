import uuid
import datetime as dt

from flask import  render_template, redirect, url_for, flash
from flask_login import current_user, login_user, logout_user, login_required
from sqlalchemy.exc import  PendingRollbackError

from .. database import init_db
from .. models import User, Animal, Breed, Cage, Occupancy, Food, CageMeal
from .. logger import get_logger
from .. api.routes import cages_get
from . forms import LoginForm, RegistrationForm, AnimalForm, CageForm, CageMaintForm
from . import bp

module_logger = get_logger(__name__)

@bp.route('/init_db',  methods=['GET'])

def init_database():
    
    init_db(need_reset = True)
    
    return render_template("index.html", title='Home Page')
    

@bp.route('/')
@bp.route('/index')
def index():
    return render_template("index.html", title='Home Page')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    print('register')
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.save()
        return redirect(url_for('.login'))

    return render_template("basic_form.html", title='Registration Page', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('.index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            users = User.query.all()
            if len(users) == 0:                
                return redirect(url_for('.register'))
            flash('Invalid username or password','danger')
            return redirect(url_for('.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('.index'))

    return render_template('basic_form.html', title='Sign In', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('.index'))

@bp.route('/animals',  methods=['GET', 'POST'])
@login_required
def animals():
    form = AnimalForm()

    if form.validate_on_submit():
        selected_breed = Breed.query.filter(Breed.species == form.species.data.species, Breed.breed_name == form.breed.data.breed_name).first()
        selected_cage = Cage.query.filter(Cage.inventory_id == form.selected_cage_id.data).first()
        new_animal_data = {
            'animal_name':form.name.data,
            'weight':form.weight.data,
            'breed': selected_breed,
            'image_url': form.image_url.data if form.image_url.data else None,
            'animal_notes': form.notes.data if form.notes.data else None,
            'personal_id': uuid.uuid4().hex,           
        }
        try:
            new_animal = Animal(**new_animal_data)
        except AssertionError as ex:
            module_logger.error(f'Error on new animal creation.')
            flash(str(ex), 'danger')
            redirect(url_for('.animals'))
        if form.additional_food.data:
            if new_animal.is_new_food(form.additional_food.data.food_name):
                new_animal.additional_foods.append(form.additional_food.data)
            else:
                flash(
                    f'Food {form.additional_food.data.food_name} is in breed {selected_breed.breed_name} foods list already.',
                    'info'
                )
        try:
            new_animal.save()
            new_occupancy_record = Occupancy(
                animal_id = new_animal.id, 
                cage_id = selected_cage.id )
            new_occupancy_record.save()
        except (ValueError, PendingRollbackError, Exception) as ex:
            flash(str(ex),'danger')
        finally:
            return redirect(url_for('.index'))

    return render_template('animals.html', title='Animals', form=form, header='Add animal to the Zoo ')

@bp.route('/animal',  methods=['GET','POST'])
@bp.route('/animal/<string:personal_id>',  methods=['GET', 'POST'])
@login_required
def animal_edit():
    form = AnimalForm()
    if form.validate_on_submit():
        db_animal = Animal.query.filter(Animal.personal_id == form.selected_animal_id.data).first()
        update_dict = {
            'animal_name': form.name.data,
            'weight': form.weight.data,
            'animal_notes': form.notes.data if form.notes.data != '' else None,
            'image_url': form.image_url.data if form.image_url.data != '' else None
        }
        if form.additional_food.data:
            db_animal.additional_foods = [form.additional_food.data]
        if form.selected_cage_id.data:
            db_cage = Cage.query.filter(Cage.inventory_id == form.selected_cage_id.data).first()
            res = cages_get(
                {'cage_id':db_cage.id, 'animal_weight':db_animal.weight, 'breed_id':db_animal.breed.id}
            )
            if isinstance(res.json,dict):
                flash(f'Cage with inventory id: {db_cage.inventory_id} can NOT accomodate animal {db_animal.breed.species} named: {db_animal.animal_name}', 'danger')
                redirect(url_for('.animals'))

            now = dt.datetime.utcnow()
            curr_occups = (Occupancy
                .query
                .filter(
                    Occupancy.animal_id == db_animal.id, 
                    Occupancy.occuped_at < now,
                    Occupancy.left_at == None
                )
                .first()
            )
            if curr_occups is not None:
                try:         
                    curr_occups.update({'left_at':now})
                except (ValueError, PendingRollbackError, Exception) as ex:            
                    redirect(url_for('.animals'))
            try:               
                new_occupancy_record = Occupancy(
                    animal_id = db_animal.id, 
                    cage_id = db_cage.id 
                )
                new_occupancy_record.save()
            except (ValueError, PendingRollbackError, Exception) as ex:            
                redirect(url_for('.animals'))

        try:
            db_animal.update(update_dict)            
        except (ValueError, PendingRollbackError, Exception) as ex:            
            redirect(url_for('.animals'))
    return render_template('animal_edit.html', title='Modify animal', form=form, header="Edit existing animal's data ")

@bp.route('/animal/maintanance',  methods=['GET','POST'])
@bp.route('/animal/maintanance/<string:personal_id>',  methods=['GET', 'POST'])
@login_required
def animal_maintanance():
    pass

    return render_template('animal_maintanance.html', title='Animal maintanance', header="Animal maintanance")

@bp.route('/cages',  methods=['GET', 'POST'])
@login_required
def cages():
    form = CageForm()
    if form.validate_on_submit():
        new_cage_data = {
            'width': form.width.data,
            'length': form.width.data,
            'height': form.width.data,
            'cage_notes': form.width.data,
        }
        try:
            new_cage = Cage(**new_cage_data)
        except AssertionError as ex:
            module_logger.error(f'Error on new cage creation.')
            flash(str(ex), 'danger')
            redirect(url_for('.cages'))
        new_cage.habitat_id = (form.habitats.data.id)
        try:
            new_cage.save()
        except (ValueError, PendingRollbackError, Exception) as ex:
            flash(str(ex),'danger')
        finally:
            return redirect(url_for('.index'))


    return render_template('cages.html', title='Cages', form=form, header="Add cage to the Zoo ")

@bp.route('/cages/maintanance',  methods=['GET', 'POST'])
@bp.route('/cages/maintanance/<string:id>',  methods=['GET', 'POST'])
@login_required
def maintanance(id = None):
    form = CageMaintForm()
    if form.validate_on_submit():
        selected_cage = Cage.query.filter(Cage.inventory_id == form.selected_cage_id.data).first()
        new_temp = float(form.curr_temp.data)
        new_temp = (new_temp 
            if new_temp <= float(selected_cage.habitat.max_temperature) 
            else float(selected_cage.habitat.max_temperature))
        new_temp = (new_temp 
            if new_temp >= float(selected_cage.habitat.min_temperature) 
            else float(selected_cage.habitat.min_temperature))
        
        try:
            selected_cage.update({'curr_temperature':new_temp})
        except (ValueError, PendingRollbackError, Exception) as ex:
            flash(str(ex),'danger')
            return redirect(url_for('.index'))
        if form.additional_food.data.food_name and form.food_qty.data:
            curr_food = Food.query.filter(Food.food_name == form.additional_food.data.food_name).first()
            meal = CageMeal(
                cage_id = selected_cage.id,
                food_id = curr_food.id,
                cage_meal_qty = float(form.food_qty.data)
            )
            try:
                meal.save()
            except (ValueError, PendingRollbackError, Exception) as ex:
                flash(str(ex),'danger')
                return redirect(url_for('.index'))
        return redirect(url_for('.maintanance'))    

    return render_template('cage_maintanance.html', title='Cages maintanance', form=form, header="Adjust cage enviroment ")
