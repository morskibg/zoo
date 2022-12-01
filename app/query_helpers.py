from dateutil import relativedelta
from sqlalchemy import func
from .helpers import convert_date_to_utc_with_hours, get_date_approximation
from .models import *
from .logger import get_logger

module_logger = get_logger(__name__)

def get_occuped_cages_by_time(time_zone = 'Europe/Sofia', curr_time = None, *, animal_id = None):
    if curr_time is None:
        curr_time = dt.datetime.utcnow()
    else:
        curr_time = convert_date_to_utc_with_hours(time_zone, curr_time)
    if animal_id is None:
        filters = (Occupancy.occuped_at < dt.datetime.utcnow(), Occupancy.left_at == None)
    else:
        filters = (
            Occupancy.occuped_at < dt.datetime.utcnow(), 
            Occupancy.left_at == None, 
            Occupancy.animal_id == animal_id,
        )
    cages = (
        Cage
            .query
            .select_from(Occupancy)
            .join(Cage, Cage.id == Occupancy.cage_id)
            .filter(*filters)
            # .filter(Occupancy.occuped_at < dt.datetime.utcnow(), Occupancy.left_at == None)
            .all()
        )

    return cages

def get_remaining_cage_env_capacity(cage):
    remaing_capacity = (
        db_session
        .query(                                             
            (cage.habitat.min_air_volume - func.coalesce(func.sum(Habitat.min_air_volume).label('min_air_volume'),0)),
            (cage.habitat.min_air_volume - func.coalesce(func.sum(Habitat.min_water_volume).label('min_water_volume'),0)),
            (cage.habitat.min_air_volume - func.coalesce(func.sum(Habitat.min_surface_area).label('min_surface_area'),0))                        
        )
        .join(Occupancy, Occupancy.animal_id ==  Animal.id)
        .join(Animal, Animal.breed_id ==  Breed.id)
        .join(Breed, Breed.habitat_id == Habitat.id)                                   
        .filter(Occupancy.cage_id == cage.id)
        .all()
    )
    try:
        remaing_capacity = remaing_capacity[0]
    except (TypeError, IndexError) as ex:
        module_logger.error(f'{ex}')
        return None
    return remaing_capacity                

def get_cage_current_energy(cage_id):
    energy = (
        db_session
        .query(                                                  
            (func.sum(Food.energy * CageMeal.cage_meal_qty)).label('cage_food_energy'),                                    
        )
        .select_from(CageMeal)
        .join(Food, Food.id ==  CageMeal.food_id)                      
        .filter(CageMeal.cage_id == cage_id)
        .all() 
    )
    return energy[0][0]

def get_cage_current_food_supply(cage_id):
    foods = (
        db_session
        .query(                                                  
            Food.food_name.label('cage_food_name'),                                    
            CageMeal.cage_meal_qty.label('cage_food_qty'),                                    
        )
        .select_from(CageMeal)
        .join(Food, Food.id ==  CageMeal.food_id)                      
        .filter(CageMeal.cage_id == cage_id)
        .all() 
    )
    return foods

def get_cage_animal_data(time_zone = 'Europe/Sofia', curr_time = None, *, cage_id):
    if curr_time is None:
        curr_time = dt.datetime.utcnow()
    else:
        curr_time = convert_date_to_utc_with_hours(time_zone, curr_time)

    cage_animal_data = (
        db_session
        .query( 
            Occupancy.animal_id,                                                 
            Breed.min_food_energy_intake.label('food_energy_req'),             
            Breed.is_predator.label('is_predator'), 
            Animal.weight.label('weight'),                                   
        )
        .join(Animal, Animal.id == Occupancy.animal_id)
        .join(Breed, Breed.id == Animal.breed_id)       
        .filter(
                Occupancy.occuped_at < curr_time, 
                Occupancy.left_at == None, 
                Occupancy.cage_id == cage_id,
            )
        .all() 
    )   

    return cage_animal_data

def update_cold_blooded_weights():
    print('updating cold blooded weights')
    curr_date = dt.datetime.utcnow()
    cold_blooded_sub = (
        db_session
        .query( 
            Occupancy.animal_id,                                         
        )        
        .join(Animal, Animal.id == Occupancy.animal_id)
        .join(Breed, Breed.id == Animal.breed_id)            
        .filter(
            Occupancy.occuped_at < curr_date, 
            Occupancy.left_at == None,                 
        )
        .filter(Breed.is_cold_blooded == True)
        .subquery()
    )
    animals = Animal.query.join(cold_blooded_sub, cold_blooded_sub.c.animal_id == Animal.id).all() 
    if not animals :
        return   
    for animal in animals:

        adjusted_target_date, adjusted_now_date = get_date_approximation(animal.updated_at, curr_date)
        delta_between_approx_dates  = relativedelta.relativedelta(adjusted_now_date, adjusted_target_date)
        aproximated_months_diff = delta_between_approx_dates.months
        print(adjusted_target_date, adjusted_now_date)  
        print(f'{aproximated_months_diff=}')  
        if not aproximated_months_diff:
            continue
        animal_new_weight = float(animal.weight) * 0.13 * aproximated_months_diff + float(animal.weight)
        try:
            animal.update({
                'weight':animal_new_weight,
                'updated_at': curr_date
            })
        except Exception as ex:
            continue

def get_initial_date():
    return InitialDate.query.first()
  
    

    



                               