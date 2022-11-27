from flask import current_app
from flask_wtf import FlaskForm
from wtforms.fields import (
    StringField, PasswordField, BooleanField, SubmitField, DateField, TextAreaField, IntegerField, FloatField,
    SelectField, IntegerField, DecimalField, FileField, SelectMultipleField, SelectField, HiddenField)

from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, Optional, NumberRange
from wtforms.widgets import PasswordInput

from .. models import *
from .. database import db_session

class TestForm(FlaskForm):
    # username = StringField('Username', validators=[DataRequired()])
    # email = StringField('Email', validators=[DataRequired()])
    # password = PasswordField('Password', validators=[DataRequired()])

    submit = SubmitField('Test')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me', default = True)
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

    submit = SubmitField('Sign In')

class InitDbForm(FlaskForm):
   
    submit = SubmitField('Sign In')

class AnimalForm(FlaskForm):

    name = StringField('Nickname', validators=[DataRequired()])
    species = QuerySelectField('Species', query_factory=lambda: Breed.query.group_by(Breed.species).all(), 
        allow_blank=False, get_label=Breed._get_species, validators=[DataRequired()], render_kw={'size': 1})
    
    breed = QuerySelectField('Breed', query_factory=lambda: Breed.query.all(), 
        allow_blank=False, get_label=Breed.__str__, validators=[DataRequired()], render_kw={'size': 1})
    breed_food = QuerySelectField('Breed Specific Food', query_factory=lambda: Breed.query.group_by(Breed.species).all(), 
        allow_blank=False, get_label=Breed._get_foods, validators=[Optional()], render_kw={'size': 1,'disabled':''})
    additional_food = QuerySelectField('Animal Specific Food', query_factory=lambda: Food.query.all(), 
        allow_blank=True, get_label=Food._get_name, validators=[Optional()], render_kw={'size': 1})
    
    weight = FloatField('Weight', validators=[DataRequired(),NumberRange(min=0.001, max=10000, message='Please provide correct weight.')])
    image_url = StringField('Img URL', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    # cages = QuerySelectField('Available cages', query_factory=lambda: Cage.query.all(), 
    #     allow_blank=True, get_label=Food._get_name, validators=[Optional()], render_kw={'size': 1})
    selected_cage_id = HiddenField("selected_cage_id")
    selected_animal_id = HiddenField("selected_animal_id")
    wtf_submit = SubmitField('Save', render_kw={'hidden': True})
class CageForm(FlaskForm):

    habitats = QuerySelectField('Habitats', query_factory=lambda: Habitat.query.all(), 
        allow_blank=False, get_label=Habitat.__str__, validators=[DataRequired()], render_kw={'size': 1})   
    width = FloatField('Width', validators=[DataRequired(),NumberRange(min=1, max=10000, message='Please provide correct Width.')])
    length = FloatField('Length', validators=[DataRequired(),NumberRange(min=1, max=10000, message='Please provide correct Length.')])
    height = FloatField('Height', validators=[DataRequired(),NumberRange(min=1, max=10000, message='Please provide correct Height.')])
    
    notes = TextAreaField('Notes', validators=[Optional()])

    wtf_submit = SubmitField('Save', render_kw={'hidden': True})

