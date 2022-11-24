import uuid
from urllib import parse

def validate_non_negative_real_number(value):
    try:
        value = float(value)
        assert value >= 0
    except (ValueError, AssertionError) as ex:
        raise AssertionError('The value must be non-negative real number')

def validate_real_number(value):
    try:
        value = float(value)        
    except ValueError as ex:
        raise AssertionError('The value must be real number')
    

def validate_text_length(value, max_len):  
    try:
        assert len(value) <= max_len and len(value) != 0
    except ValueError as ex:
        raise AssertionError(f'The length of the textmust be under or equal to {max_len}')
     
def validate_boolean(value):
    try:
        assert type(bool(value)) == bool       
    except ValueError as ex:
        raise AssertionError('The value must be boolean')

def validate_uuid(value):
    try:
        assert uuid.UUID(value)      
    except ValueError as ex:
        raise AssertionError('The value must be valid UUID v4')

def validate_url(value):
    try:
        parsed_value = parse.urlparse(value)
        assert  parsed_value.scheme and parsed_value.netloc    
    except ValueError as ex:
        raise AssertionError('The value must be valid URL')
    