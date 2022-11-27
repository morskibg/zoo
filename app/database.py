
import pandas as pd
import datetime as dt
import uuid
import random
import math
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import OperationalError

from .logger import get_logger
from . helpers import generate_habitat_composite

from config import Config


module_logger = get_logger(__name__)

engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI, 
    convert_unicode=True,
    connect_args={"check_same_thread": False}
    )

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def init_db(need_reset = False):
    if need_reset:
        drop_db()
    try: 
        sql = f"SELECT * FROM association_table_breed_food WHERE 1"
        query = engine.execute(sql) 
        _ = query.first()[0]
    except (OperationalError, TypeError) as ex:        
        drop_db()
        Base.metadata.create_all(bind=engine)    
        seed_db()


def seed_db():
    from .models import Food, Movement, Breed, Habitat, Cage, CageMeal
    module_logger.info('Seeding DB')

    f_m_dict = {
        'food':['meat', 'milk', 'fish', 'insect', 'grass', 'vegetable', 'fruit', 'grain', 'plant', 'mixed', 'granulated'],
        'movement':['fly', 'swim', 'walk', 'crawl','jump']
    }
    
    food_types_dic = {
        'meat':'chicken', 'milk':'condesed milk', 'fish':'salmon', 'insect':'fly', 'grass':'cynodon dactylon', 
        'vegetable':'paprika', 'fruit':'apple', 'grain':'soy', 'plant':'algae', 'mixed':'mixed', 'granulated':'granulated'
    }
    for key in f_m_dict.keys():
         
        if key == 'food':
            df = pd.DataFrame({'food_type':f_m_dict[key]}) 
            df['food_name'] = df['food_type'].apply(lambda x: food_types_dic[x])      
            df['energy'] = df['food_name'].apply(lambda x: random.randint(1,5000))    
        else:
            df = pd.DataFrame({'movement_name':f_m_dict[key]})

        df.to_sql(
            key,
            con=engine,
            if_exists='append',
            chunksize=1000,
            index=False
        )

    breed_seed_df = pd.read_csv('breeds.csv')
    for _, row in breed_seed_df.iterrows():
        db_habitats_composites = [x[0] for x in db_session.query(Habitat.composite_id).all()]
        habitat_tokens = row.habitat.split(';')
        curr_notes = habitat_tokens[9]     
        curr_composite = generate_habitat_composite(habitat_tokens[:-1])        
        if curr_composite in db_habitats_composites:
            curr_breed_habitat = Habitat.query.filter(Habitat.composite_id == curr_composite).first()
        else:
            curr_breed_habitat = Habitat(
                min_air_volume = habitat_tokens[0],
                min_water_volume = habitat_tokens[1],
                min_surface_area = habitat_tokens[2],
                min_temperature = habitat_tokens[3],                   
                max_temperature = habitat_tokens[4],                    
                min_humidity = habitat_tokens[5],
                max_humidity = habitat_tokens[6],
                min_uv_index = habitat_tokens[7],
                max_uv_index = habitat_tokens[8],
                composite_id = curr_composite,
                habitat_notes = curr_notes,
            )
            curr_breed_habitat.save() 
        random_animals_count_per_cage = random.randrange(1,40)
        cage_habitat = Habitat(
            min_air_volume = float(curr_breed_habitat.min_air_volume) * random_animals_count_per_cage,
            min_water_volume = float(curr_breed_habitat.min_water_volume) * random_animals_count_per_cage,
            min_surface_area = float(curr_breed_habitat.min_surface_area) * random_animals_count_per_cage,
            min_temperature = curr_breed_habitat.min_temperature,
            max_temperature = curr_breed_habitat.max_temperature,
            min_humidity = curr_breed_habitat.min_humidity,
            max_humidity = curr_breed_habitat.max_humidity,
            min_uv_index = curr_breed_habitat.min_uv_index,
            max_uv_index = curr_breed_habitat.max_uv_index,
            composite_id = '0',
            habitat_notes = curr_notes,
        )
        cage_composite = generate_habitat_composite(
            [
               cage_habitat.min_air_volume,
               cage_habitat.min_water_volume,
               cage_habitat.min_surface_area,
               cage_habitat.min_temperature,
               cage_habitat.max_temperature,
               cage_habitat.min_humidity,
               cage_habitat.max_humidity,
               cage_habitat.min_uv_index,
               cage_habitat.max_uv_index,               
            ]
        )
        db_cage_habitat = Habitat.query.filter(Habitat.composite_id == cage_composite).first()
        if db_cage_habitat:
            cage_habitat = db_cage_habitat
        else:
            cage_habitat.save()
        length = random.randrange(30,50) 
        height = random.randrange(2,7)        
        width = math.ceil(cage_habitat.min_surface_area / length)
        cage = Cage(
            habitat_id = cage_habitat.id,
            inventory_id = uuid.uuid4().hex,
            cage_name = None,
            curr_temperature = random.randrange(int(curr_breed_habitat.min_temperature), int(curr_breed_habitat.max_temperature)),  
            width = width,
            length = length,
            height = height,
            cage_notes = None
        )
        cage.save()

        curr_breed = Breed(
            breed_name = str(row['name']).lower(),
            species = str(row.species).lower(),
            min_weight = row.min_weight,
            min_body_temp = row.min_body_temp,
            max_body_temp = row.max_body_temp,
            min_food_energy_intake = row.min_food_energy_intake,
            max_food_energy_intake = row.max_food_energy_intake,
            is_cold_blooded = row.is_cold_blooded,
            is_predator = row.is_predator,
            breed_notes = None                         
        )        

        for food_type in row.food.split(';'):
            db_food = Food.query.filter(Food.food_type == str(food_type).lower()).first()
            curr_breed.breed_foods.append(db_food)
            cage_meal = CageMeal(
                cage_id = cage.id,
                food_id = db_food.id,
                cage_meal_qty = random.randint(1,100)
            )
            cage_meal.save()


        for movement in row.movement.split(';'):
            db_movement = Movement.query.filter(Movement.movement_name == str(movement).lower()).first()
            curr_breed.movements.append(db_movement)
            
        curr_breed_habitat.breeds.append(curr_breed) 
        curr_breed.save() 


    animal_seed_df  = pd.read_csv('animals.csv')
    animal_seed_df['id'] = animal_seed_df.index + 1
    animal_seed_df['personal_id'] = [uuid.uuid4().hex for _ in range(len(animal_seed_df))]  
    animal_seed_df['inserted_at'] = dt.datetime.utcnow()
    animal_seed_df['updated_at'] = dt.datetime.utcnow()
    animal_seed_df.to_sql(
        'animal',
        con=engine,
        if_exists='append',
        chunksize=1000,
        index=False
    )

    
    

def drop_db():
    module_logger.info('Dropping DB')
    Base.metadata.drop_all(bind=engine)

