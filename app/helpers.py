

from urllib import parse
import pandas as pd
import numpy as np
import datetime as dt
import pytz



from .logger import get_logger

module_logger = get_logger(__name__)


def parse_urlargs(url):
    query = parse.parse_qs(parse.urlparse(url).query)
    return {k:v[0] if v and len(v) == 1 else v for k,v in query.items()}

def generate_habitat_composite(habitat_data_list):
    tokens_df = pd.DataFrame({'tokens':habitat_data_list})
    tokens_df = tokens_df.replace(r'', 0)
    tokens_df['tokens'] = tokens_df['tokens'].apply(lambda x: f'{float(x):.4f}')
    habitat_tokens = list(tokens_df['tokens'])
    return ''.join(habitat_tokens)

def is_suitable_cage_habitat_for_breed(breed, cage):
    
    return (
        cage.habitat.min_air_volume >= breed.habitat.min_air_volume and
        cage.habitat.min_water_volume >= breed.habitat.min_water_volume and
        cage.habitat.min_surface_area >= breed.habitat.min_surface_area and
        abs(cage.habitat.min_temperature) <= abs(breed.habitat.min_temperature) and
        abs(cage.habitat.max_temperature) <= abs(breed.habitat.max_temperature) and
        cage.habitat.min_humidity >= breed.habitat.min_humidity and
        cage.habitat.max_humidity <= breed.habitat.max_humidity and
        cage.habitat.min_uv_index >= breed.habitat.min_uv_index and
        cage.habitat.max_uv_index <= breed.habitat.max_uv_index
    )

def date_parser(dt_obj, t_format="%Y-%m-%d %H:%M:%S"):    
    if isinstance(dt_obj, str):
        try:
            dt_obj = dt.datetime.strptime(dt_obj, t_format)
        except ValueError as ex:
            module_logger.error(f'Error on parsing {dt_obj} with {t_format} format.')            
            module_logger.error(f'{ex}')
            dt_obj = None
    return dt_obj

def convert_date_to_utc_with_hours(dt_str, time_zone = 'Europe/Sofia', t_format="%Y-%m-%d %H:%M:%S"):
    if dt_str == "":
        return None        
    if isinstance(dt_str, dt.date):
        try:
            dt_str = dt_str.strftime(t_format)
        except ValueError as ex:
            module_logger.error(f'Error on parsing str {dt_str} to dt with {t_format} format.')            
            module_logger.error(f'{ex}')
            return None 
    try:   
        naive = dt.datetime.strptime(dt_str, t_format)
        local = pytz.timezone(time_zone)
        local_date = local.localize(naive, is_dst=True)
        return local_date.astimezone(pytz.utc).replace(tzinfo=None)
    except ValueError as ex:
            module_logger.error(f'Error on parsing {dt_str} with {t_format} format.')            
            module_logger.error(f'{ex}')
            return None 
    


def is_safe_to_add_animal_to_cage(is_predator_in_cage, weight_in_cage, is_predator, weight):
    if not is_predator_in_cage and not is_predator:
        return True
    if not is_predator_in_cage and is_predator:
        return False
    if is_predator_in_cage or is_predator:
        return abs(weight_in_cage - weight) > (min(weight_in_cage , weight)) * 10
    
# def get_suitable_cages_by_breed(breed, * ,animal = None, cage_id = None):
#     cages = get_cages(cage_id)
    
#     cages = [x for x in cages if is_suitable_cage_habitat_for_breed(animal.breed, x)]

