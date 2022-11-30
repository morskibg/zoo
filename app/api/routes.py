import pandas as pd
from flask import request, jsonify, redirect, url_for


from .. models import *
from .. helpers import (parse_urlargs, 
                        is_suitable_cage_for_breed, 
                        is_safe_to_add_animal_to_cage)

from .. query_helpers import (get_occuped_cages_by_time,
                             get_remaining_cage_env_capacity, 
                             get_cage_animal_data,
                             get_initial_cage_energy,
                             
                             )
from . import bp



@bp.route('/animals', methods=['GET'])
@bp.route('/animals/<string:personal_id>', methods=['GET']) #methods=['GET','POST','PUT','DELETE'])
def animals(personal_id = None):
    animal_schema = AnimalSchema()
    query_dict = parse_urlargs(request.url)
    if query_dict:
        pass

    else:
        animals = (Animal.query.all() 
            if personal_id is None 
            else Animal.query.filter(Animal.personal_id == personal_id).first()
        )             
        try:
            return jsonify(animal_schema.dump(animals, many=personal_id is None))
        except:            
            return jsonify([])

@bp.route('/breeds', methods=['GET'])
@bp.route('/breeds/<string:arg>', methods=['GET']) 
def breeds(arg = None):
    breed_schema = BreedSchema()
    filters = []
    if arg is not None:
        try:
            id = int(arg)
            filters.append(Breed.species == Breed.query.get(id).species)
        except Exception as ex:
            filters.append(Breed.species == arg)
        
    query_dict = parse_urlargs(request.url)
    if query_dict:
        pass

    else:
        breeds = (Breed.query.all() 
            if arg is None 
            else Breed.query.filter(*filters)
        )       
        try:
            return jsonify(breed_schema.dump(breeds, many=True))
        except:            
            return jsonify([])

@bp.route('/cages', methods=['GET'])
@bp.route('/cages/<string:arg>', methods=['GET']) 
def cages_get(kwarg_dict = None): 
    cage_schema = CageSchema() 
    cages = Cage.query.all()

    if kwarg_dict is not None:
        query_dict = {}
        if 'cage_id' in kwarg_dict.keys():
            cages = Cage.query.filter(Cage.id == kwarg_dict['cage_id']).all()  
        if 'animal_weight' in kwarg_dict.keys():
            query_dict['animal_weight'] = kwarg_dict['animal_weight']
        if 'breed_id' in kwarg_dict.keys():
            query_dict['breed_id'] = kwarg_dict['breed_id']

    else:        
        query_dict = parse_urlargs(request.url)

    suitable_cages = []
    if query_dict:
        
        if 'breed_id' in query_dict:
            selected_breed = Breed.query.get(int(query_dict['breed_id']))
            cages = [x for x in cages if is_suitable_cage_for_breed(selected_breed, x)]
            
            animal_weight = None if query_dict['animal_weight'] == 'null' else float(query_dict['animal_weight'])
            print(f'{animal_weight=}')
            for cage in cages: 
                max_weight = 0
                min_weight = 0
                remaing_capacity = get_remaining_cage_env_capacity(cage)
                initial_cage_energy = get_initial_cage_energy(cage.id)
                cage_animals_data = get_cage_animal_data(cage_id = cage.id)
                print(f'{cage.inventory_id=}')               
                # print(f'{remaing_capacity=}')               
                if remaing_capacity is None:
                    continue   
                is_become_overwhelmed = any(
                    list(
                        map(
                            lambda x: x[0] < x[1], zip(
                                remaing_capacity,
                                [selected_breed.habitat.min_air_volume, 
                                selected_breed.habitat.min_water_volume, 
                                selected_breed.habitat.min_surface_area]
                            )
                        )
                    )
                )
                               
                if is_become_overwhelmed:
                    continue
                if cage_animals_data:
                    cage_animals_data_df = pd.DataFrame.from_records(cage_animals_data, columns = cage_animals_data[0].keys())
                    cage_animals_data_df['weight'] = cage_animals_data_df['weight'].astype(float)
                remaing_food_energy = (initial_cage_energy 
                    if not cage_animals_data 
                    else initial_cage_energy - float(cage_animals_data_df['food_energy_req'].sum()))
                # print(f'{remaing_food_energy=}')                                   
                if remaing_food_energy <= 0:
                    continue 
                animals_count = ( 0 
                    if not cage_animals_data 
                    else cage_animals_data_df.shape[0])
                has_predator = False if not cage_animals_data else cage_animals_data_df['is_predator'].any()
                cage.energy = remaing_food_energy
                cage.animals_count = animals_count
                cage.has_predator = int(has_predator)
                if has_predator:
                    min_weight = float(cage_animals_data_df['weight'].min()) 
                    max_weight = float(cage_animals_data_df['weight'].max())
                cage.max_predator_weight = max_weight 
                cage.min_predator_weight = min_weight 
                
                if not cage_animals_data or animal_weight is None:
                    is_safe = True 
                else:
                    cage_animals_data_df['is_safe'] = \
                        cage_animals_data_df.apply(
                            lambda x: 
                            is_safe_to_add_animal_to_cage(x['is_predator'], x['weight'], selected_breed.is_predator, animal_weight),
                            axis = 1
                        )
                    is_safe = cage_animals_data_df['is_safe'].all()
                
                cage.is_safe = int(is_safe)
                suitable_cages.append(cage)

        elif 'animal_id' in query_dict: 
            suitable_cages = get_occuped_cages_by_time(animal_id = query_dict['animal_id'])   
    else:
        
        for cage in cages:
            max_weight = 0
            min_weight = 0
            remaing_capacity = get_remaining_cage_env_capacity(cage)
            initial_cage_energy = get_initial_cage_energy(cage.id)
            cage_animals_data = get_cage_animal_data(cage_id = cage.id)
            if cage_animals_data:
                cage_animals_data_df = pd.DataFrame.from_records(cage_animals_data, columns = cage_animals_data[0].keys())
                cage_animals_data_df['weight'] = cage_animals_data_df['weight'].astype(float)
            remaing_food_energy = (initial_cage_energy 
                if not cage_animals_data 
                else initial_cage_energy - float(cage_animals_data_df['food_energy_req'].sum()))
            # print(f'{remaing_food_energy=}')    
            animals_count = ( 0 
                if not cage_animals_data 
                else cage_animals_data_df.shape[0])
            has_predator = False if not cage_animals_data else cage_animals_data_df['is_predator'].any()
            cage.energy = remaing_food_energy
            cage.animals_count = animals_count
            cage.has_predator = int(has_predator)
            if has_predator:
                min_weight = float(cage_animals_data_df['weight'].min()) 
                max_weight = float(cage_animals_data_df['weight'].max())
            cage.max_predator_weight = max_weight 
            cage.min_predator_weight = min_weight             
            
            suitable_cages.append(cage)                 
    try:
        return jsonify(cage_schema.dump(suitable_cages, many=len(suitable_cages)))
    except:            
        return jsonify([])

@bp.route('/occupancy', methods=['GET'])
@bp.route('/occupancy/<string:personal_id>', methods=['GET'])
def occupancy(personal_id = None): 
    
        occupancy_schema = OccupancySchema() 
        occupancy = Occupancy.query.all() if personal_id is None else Occupancy.query.filter(Occupancy.personal_id == personal_id)
        try:        
            return jsonify(occupancy_schema.dump(occupancy, many=True))
        except:            
            return jsonify([])  

@bp.route('/foods', methods=['GET'])
@bp.route('/foods/<string:personal_id>', methods=['GET'])
def food(personal_id = None): 
    
    food_schema = FoodSchema() 
    food = Food.query.all() 
    try:        
        return jsonify(food_schema.dump(food, many=True))
    except:            
        return jsonify([])       

