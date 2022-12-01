import sys
import datetime as dt
import uuid
from functools import total_ordering

from sqlite3 import IntegrityError
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Table, Text
from sqlalchemy.orm import  validates, relationship, backref
from sqlalchemy.exc import SQLAlchemyError, PendingRollbackError
from sqlalchemy.orm.exc import FlushError
from flask import flash
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow_sqlalchemy import  auto_field
from marshmallow import fields

from app import login, ma
from .database import Base, db_session
from .validators import validate_real_number, validate_non_negative_real_number, validate_text_length, validate_boolean, validate_uuid, validate_url
from . helpers import generate_habitat_composite
from . logger import get_logger

module_logger = get_logger(__name__)

class BaseModel(Base):
    __abstract__ = True
    def save(self):
        try:
            if self not in db_session:
                db_session.add(self)
            db_session.commit()                      
        except (FlushError, PendingRollbackError, SQLAlchemyError, IntegrityError, Exception) as ex: 
            module_logger.error(f'Error on saving in database.')            
            module_logger.error(f'{ex.__class__.__name__} - {ex}')
            module_logger.error(f'Exception at row --->{sys.exc_info()[2].tb_lineno} from {__name__}')
            raise ValueError(f'Error on saving in database !')            
        else: 
            try:
                flash(f'{self} saved in db successfully','success')
            except:
                pass
            module_logger.info(f'{self} commiting to db')

    def update(self, data: dict):
        for field, value in data.items():            
            setattr(self, field, value)
        try:
            self.save()            
        except ValueError as ex:            
            module_logger.error(f'Error on updating {self} in database.')          
            raise      
        else:
            try:
                flash(f'{self} updated successfully','success')
            except:
                pass
            module_logger.info(f'{self} updated successfully')

    def delete(self):        
        try:
            db_session.delete(self)
            db_session.commit()            
        except (PendingRollbackError, SQLAlchemyError, IntegrityError, Exception) as ex:            
            module_logger.error(f'Error on deleting {self} from database.')            
            module_logger.error(f'{ex}')
            module_logger.error(f'Exception at row --->{sys.exc_info()[2].tb_lineno}') 
            raise ValueError(f'Error on updating {self} in database !')       
        else:
            try:
                flash(f'{self} deleted successfully','success')
            except:
                pass
            module_logger.info(f'{self} deleted successfully')

class User(UserMixin, BaseModel):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), index=True, unique=True)
    email = Column(String(120), index=True, unique=True)
    password_hash = Column(String(128), nullable=False) # nullable=False

    def get_email(self):
        return self.email

    def __repr__(self):
        return f'{self.username}'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login.user_loader
def load_user(id):    
    return User.query.get(int(id))

association_table_breed_food = Table(
    "association_table_breed_food",
    Base.metadata,
    Column("breed_id", ForeignKey("breed.id"), primary_key = True),
    Column("food_id", ForeignKey("food.id"), primary_key = True),
)

association_table_breed_movement = Table(
    "association_table_breed_movement",
    Base.metadata,
    Column("breed_id", ForeignKey("breed.id"), primary_key = True),
    Column("movement_id", ForeignKey("movement.id"), primary_key = True),
)

association_table_animal_additional_food = Table(
    "association_table_animal_additional_food",
    Base.metadata,
    Column("animal_id", ForeignKey("animal.id"), primary_key = True),
    Column("food_id", ForeignKey("food.id"), primary_key = True),
)

class InitialDate(BaseModel):
    __tablename__ = 'initial_date'
    initial_date = Column(DateTime, primary_key = True, default=dt.datetime.utcnow)

class Movement(BaseModel):
    __tablename__ = 'movement'
    id = Column(Integer, primary_key = True)
    movement_name = Column(String(8), nullable = False, unique = True)
    breeds = relationship("Breed", secondary = association_table_breed_movement,back_populates = "movements")

    @validates('move')
    def validate_move(self, key, field):
        if field.lower() not in ['fly', 'swim', 'walk', 'crawl', 'jump']:
            raise AssertionError("Movement must be one of 'fly', 'swim', 'walk', 'crawl' or 'jump'")
        return field

class AnimalMeal(BaseModel):
    __tablename__ = 'animal_meal'
    animal_id = Column(ForeignKey("animal.id"), primary_key=True)
    food_id = Column(ForeignKey("food.id"), primary_key=True)
    served_at = Column(DateTime, default=dt.datetime.utcnow)  
    animal_meal_qty = Column(Float(9,5), nullable = False)
    animal_foods = relationship("Food")

class CageMeal(BaseModel):
    __tablename__ = 'cage_meal'
    cage_id = Column(ForeignKey("animal.id"), primary_key=True)
    food_id = Column(ForeignKey("food.id"), primary_key=True)
    added_at = Column(DateTime, default=dt.datetime.utcnow)  
    cage_meal_qty = Column(Float(9,5), nullable = False)
    cage_foods = relationship("Food")   

class Occupancy(BaseModel):
    __tablename__ = 'occupancy'
    animal_id = Column(ForeignKey("animal.id"), primary_key=True)
    cage_id = Column(ForeignKey("cage.id"), primary_key=True)
    occuped_at = Column(DateTime, default=dt.datetime.utcnow)   
    left_at = Column(DateTime, nullable = True, default = None)
    cages = relationship("Cage", back_populates="occups")
    animals = relationship("Animal", back_populates="occups")    
    

class Food(BaseModel):
    __tablename__ = 'food'
    id = Column(Integer, primary_key = True)
    food_name = Column(String(32), nullable = False, unique = True)
    food_type = Column(String(8), nullable = False)
    energy = Column(Float(5,1), nullable = False)
    food_notes = Column(Text, nullable = True)
    breeds = relationship("Breed", secondary = association_table_breed_food, back_populates = "breed_foods")
    animals = relationship("Animal", secondary = association_table_animal_additional_food, back_populates = "additional_foods")
      
    @validates('food_type','food_name')
    def validate_move(self, key, field):
        if key == 'food_type' and field.lower() not in ['meat', 'milk', 'fish', 'insect','grass', 'vegetable', 'fruit', 'grain', 'plant', 'mixed', 'granulated']:
            raise AssertionError(
                "Food type must be one of 'meat', 'milk', 'fish', 'insect','grass', 'vegetable', 'fruit', 'grain', 'plant', 'mixed' or 'granulated'"
                )
        else:
            validate_text_length(field, 32)

        return field

    def _get_name(self):
        return f'{self.food_name}'


class Animal(BaseModel):
    __tablename__ = 'animal'
    id = Column(Integer, primary_key = True)
    personal_id = Column(String(32), nullable = False, unique = True)
    animal_name = Column(String(32), nullable = False)
    weight = Column(Float(7,3), nullable = False)
    animal_notes = Column(Text, nullable = True)
    breed_id = Column(Integer, ForeignKey('breed.id', ondelete='CASCADE',onupdate = 'CASCADE'))       
    image_url = Column(String(256), nullable = True)   
    inserted_at =Column(DateTime, default=dt.datetime.utcnow)  
    updated_at =Column(DateTime, default=dt.datetime.utcnow)    
    breed = relationship('Breed', back_populates = "animals")    
    additional_foods = relationship("Food", secondary = association_table_animal_additional_food, back_populates = "animals")  
    meals = relationship("AnimalMeal")
    occups = relationship("Occupancy", back_populates="animals")

    @validates(
        'animal_name','personal_id',
        'weight','animal_notes', 'image_url'
        )
    def validate_animal(self, key, field):           
        if (field is None and key in ['animal_notes','image_url']):
            return field
        if key in ['animal_notes','animal_name']:
            validate_text_length(field, 512)
        elif key == 'weight':
            validate_non_negative_real_number(field) 
        elif key == 'personal_id':
            validate_uuid(field)
        else:
            validate_url(field) 
        return field

    def is_new_food(self, food_name):
        return food_name not in [x.food_name for x in self.breed.breed_foods]

    def __repr__(self):
        return f"<Animal name: {self.animal_name} ; breed: {self.breed} ; id: {self.personal_id}; add_food: {self.additional_foods}>"

class Breed(BaseModel):
    __tablename__ = 'breed'
    id = Column(Integer, primary_key = True)
    habitat_id = Column(Integer, ForeignKey('habitat.id', ondelete='CASCADE',onupdate = 'CASCADE'))
    breed_name = Column(String(32), unique = True, nullable = False)
    species = Column(String(64), nullable = False)
    min_weight = Column(Float(7,3), nullable = False)
    min_body_temp = Column(Float(3,1), nullable = False)    
    max_body_temp = Column(Float(3,1), nullable  =False)
    min_food_energy_intake = Column(Float(6,1), nullable =False)
    max_food_energy_intake = Column(Float(6,1), nullable =False)
    is_cold_blooded = Column(Boolean, nullable = False)      
    is_predator = Column(Boolean, nullable = False)
    breed_notes = Column(Text, nullable = True)
    habitat = relationship("Habitat", back_populates="breeds")
    breed_foods = relationship("Food", secondary = association_table_breed_food, back_populates = "breeds")
    movements = relationship("Movement", secondary = association_table_breed_movement, back_populates = "breeds") 
    animals = relationship('Animal', back_populates = "breed")

    @validates(
        'breed_name','species',
        'min_weight','min_body_temp','max_body_temp','body_temp',
        'is_cold_blooded','is_predator','breed_notes'
        )
    def validate_breed(self, key, field):           
        if (field is None and key == 'breed_notes'):
            return field
        if key in ['notes','breed_name','species']:
            validate_text_length(field, 512)
        elif key in [
            'min_weight','min_body_temp',
            'min_body_temp','max_body_temp']:
            validate_non_negative_real_number(field) 
        else:
            validate_boolean(field) 
        return field

    def _get_species(self):
        return self.species

    def _get_foods(self):
        return ", ".join([x.food_name for x in self.breed_foods])

    def __str__(self): 
        return f'{self.breed_name}'


class Habitat(BaseModel):
    __tablename__ = 'habitat'
    id = Column(Integer, primary_key = True)    
    min_air_volume = Column(Float(8,1), nullable = True, default = 0)
    min_water_volume = Column(Float(8,1), nullable = True, default = 0)
    min_surface_area = Column(Float(5,1), nullable = False)
    min_temperature = Column(Float(4,2), nullable = False)
    max_temperature = Column(Float(4,2), nullable = False)
    min_humidity = Column(Float(3,1), nullable = True, default = 0)
    max_humidity = Column(Float(3,1), nullable = True, default = 0)
    min_uv_index = Column(Integer, nullable = True, default = 0)
    max_uv_index = Column(Integer, nullable = True, default = 0)  
    composite_id = Column(String(128), unique = True, default = '0')  
    habitat_notes = Column(Text, nullable = True)
    breeds = relationship("Breed")    
    cages = relationship("Cage")  

    attr_arr =['min_air_volume','min_water_volume','min_surface_area',
                        'min_temperature','max_temperature','min_humidity',
                        'max_humidity','min_uv_index','max_uv_index'] 


    @validates(
        'min_air_volume','min_water_volume','min_surface_area',
        'min_temperature','max_temperature','min_humidity','max_humidity',
        'min_uv_index','max_uv_index', 'habitat_notes','composite_id'
        )
    def validate_habitat(self, key, field):           
        if ((field is None or field == '') and key in 
            ['min_air_volume','min_water_volume','min_humidity', 'max_humidity', 'min_uv_index', 'max_uv_index', 'habitat_notes']):
            return 0 if key != 'habitat_notes' else None
        if key == 'composite_id':            
            field = generate_habitat_composite([str(self.__dict__[x]) for x in self.attr_arr])
        elif key == 'habitat_notes':
            validate_text_length(field, 512)
        elif key in ['min_temperature','max_temperature']:
            validate_real_number(field) 
        else:
            validate_non_negative_real_number(field) 
        return field

    def __str__(self): 
        return f'<Habitat> with air volume: {round(self.min_air_volume)}, water volume: {round(self.min_water_volume)}, min temp: {round(self.min_temperature)} , max temp: {round(self.max_temperature)}'

    def __repr__(self): 
        return f'<Habitat> with {self.min_surface_area} sq m'


class Cage(BaseModel):
    __tablename__ = 'cage'
    id = Column(Integer, primary_key = True)
    cage_name = Column(String(32), nullable = True)
    habitat_id = Column(Integer, ForeignKey('habitat.id', ondelete='CASCADE',onupdate = 'CASCADE'))
    inventory_id = Column(String(32), unique = True, default = uuid.uuid4().hex)
    width = Column(Float(6,2), nullable = False)
    length = Column(Float(6,2), nullable = False)
    height = Column(Float(6,2), nullable = False)
    curr_temperature = Column(Float(4,2), nullable = False)
    cage_notes = Column(Text, nullable = True)
    inserted_at =Column(DateTime, default=dt.datetime.utcnow)
    updated_at =Column(DateTime, default=dt.datetime.utcnow)
    habitat = relationship("Habitat", back_populates="cages")
    occups = relationship("Occupancy", back_populates="cages")
    

    @validates(
        'width','cage_name',
        'length','height','curr_temperature',
        'cage_notes'
        )
    def validate_cage(self, key, field):           
        if (field is None and key in ['cage_notes','cage_name']):
            return field
        if key == 'cage_notes':
            validate_text_length(field, 32)
        elif key == 'cage_name':
            validate_text_length(field, 512)
        elif key in ['length','width','height']:
            validate_non_negative_real_number(field) 
        elif key == 'curr_temperature':
            validate_real_number(field)
        else:
            validate_boolean(field) 
        return field

       

class FoodSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Food
        include_relationships = True
        load_instance = True
    id = auto_field()
    food_name = auto_field()    
    food_notes = auto_field()

    
class HabitatSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Habitat
        include_relationships = True
        load_instance = True
    id = auto_field()
    min_air_volume = auto_field()
    min_water_volume = auto_field()
    min_surface_area = auto_field()
    min_temperature = auto_field()
    max_temperature = auto_field()
    min_humidity = auto_field()
    max_humidity = auto_field()
    min_uv_index = auto_field()
    max_uv_index = auto_field()   
    habitat_notes = auto_field()  

class CageSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Cage
        include_relationships = True
        load_instance = True
        
    
    id = auto_field()    
    cage_name = auto_field()    
    inventory_id = auto_field()
    width = auto_field()
    length = auto_field()
    height = auto_field()
    curr_temperature = auto_field()
    cage_notes = auto_field()
    inserted_at = auto_field()
    updated_at = auto_field() 
    habitat = ma.Nested(HabitatSchema)
    energy = fields.Method("get_energy")
    animals_count = fields.Method("get_animals_count")
    max_predator_weight = fields.Method("get_max_predator_weight")
    min_predator_weight = fields.Method("get_min_predator_weight")
    has_predator = fields.Method("get_has_predator")
    is_safe = fields.Method("get_is_safe")
    foods = fields.Method("get_foods")

    def get_energy(self, obj):
        if hasattr(obj, "energy"):
            return obj.energy
        return None

    def get_animals_count(self, obj):
        if hasattr(obj, "animals_count"):
            return obj.animals_count
        return None

    def get_max_predator_weight(self, obj):
        if hasattr(obj, "max_predator_weight"):
            return obj.max_predator_weight
        return None

    def get_min_predator_weight(self, obj):
        if hasattr(obj, "min_predator_weight"):
            return obj.min_predator_weight
        return None

    def get_has_predator(self, obj):
        if hasattr(obj, "has_predator"):
            return obj.has_predator
        return None

    def get_is_safe(self, obj):
        if hasattr(obj, "is_safe"):
            return obj.is_safe
        return None
    
    def get_foods(self, obj):
        if hasattr(obj, "foods"):
            return obj.foods
        return None
    
class MovementSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Movement
        include_relationships = True
        load_instance = True
    id = auto_field()
    movement_name = auto_field() 
    
class BreedSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Breed
        include_relationships = True
        load_instance = True
    id = auto_field()
    breed_name = auto_field()
    species = auto_field()
    min_weight = auto_field()
    min_body_temp = auto_field()
    max_body_temp = auto_field()
    is_cold_blooded = auto_field()
    is_predator = auto_field()
    breed_notes = auto_field()  
    breed_foods = ma.Nested(FoodSchema, many=True) 
    habitat = ma.Nested(HabitatSchema) 
    movements = ma.Nested(MovementSchema, many=True)  
  
class AnimalSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Animal
        include_relationships = True
        load_instance = True       
    id = auto_field()
    personal_id = auto_field()
    animal_name = auto_field()
    weight = auto_field()
    animal_notes = auto_field()
    image_url = auto_field()
    inserted_at = auto_field()
    updated_at = auto_field()    
    breed = ma.Nested(BreedSchema) 
    additional_foods = ma.Nested(FoodSchema, many=True)
    current_temp = fields.Method("get_current_temp")

    def get_current_temp(self, obj):
        if hasattr(obj, "current_temp"):
            return obj.current_temp
        return None
    
class OccupancySchema(ma.SQLAlchemySchema):
    class Meta:
        model = Occupancy
        include_relationships = True
        load_instance = True  
    animal_id = auto_field()
    cage_id = auto_field()
    occuped_at = auto_field()
    left_at = auto_field()
    cages = ma.Nested(CageSchema, many=False)
class CageMealSchema(ma.SQLAlchemySchema):
    class Meta:
        model = CageMeal
        include_relationships = True
        load_instance = True  
    cage_id = auto_field()
    food_id = auto_field()
    added_at = auto_field()
    cage_meal_qty = auto_field()
    cage_foods = ma.Nested(FoodSchema, many=False)



    