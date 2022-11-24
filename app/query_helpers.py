from sqlalchemy import func
from .helpers import convert_date_to_utc_with_hours
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
    

def get_remainig_cage_food_energy(cage, is_all_cages_empty=False):        
    if is_all_cages_empty:    
        remaing_food_energy = (
            db_session
            .query(                                                  
                (func.sum(Food.energy*CageMeal.cage_meal_qty)).label('remaing_food_energy'),                                    
            )
            .select_from(CageMeal)
            .join(Food, Food.id ==  CageMeal.food_id)                      
            .filter(CageMeal.cage_id == cage.id)
            .all() 
        )
    else:
        remaing_food_energy = (
            db_session
            .query(                                                  
                (func.sum(Food.energy*CageMeal.cage_meal_qty) - Breed.min_food_energy_intake).label('remaing_food_energy'),                                    
            )
            .select_from(CageMeal)
            .join(Food, Food.id ==  CageMeal.food_id)
            .join(Animal, Animal.id == Occupancy.animal_id)
            .join(Breed, Breed.id == Animal.breed_id)               
            .filter(Occupancy.cage_id == cage.id)
            .filter(CageMeal.cage_id == cage.id)
            .all() 
        )

    try:
        remaing_food_energy = remaing_food_energy[0][0]
    except (TypeError, IndexError) as ex:
        module_logger.error(f'{ex}')
        return None
    return remaing_food_energy
                               