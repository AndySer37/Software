import os

from duckietown_utils import logger
from duckietown_utils.constants import get_scuderia_path
from duckietown_utils.exception_utils import raise_wrapped, raise_desc
from duckietown_utils.exceptions import DTUserError
from duckietown_utils.text_utils import indent


# Format of the Scuderia contents
# robot-name:
#  username: <username>
#  owner_duckietown_id: <duckietown ID> 

class ScuderiaEntry():
    def __init__(self, robot_name, username, owner_duckietown_id):
        """ 
            robot_name = emma
            username = andrea
            owner_duckietown_id = censi  
        """
        self.robot_name = robot_name
        self.username = username
        self.owner_duckietown_id = owner_duckietown_id

class ScuderiaException(DTUserError):
    pass
    

def get_scuderia_contents():
    ''' Returns the contents of the scuderia file 
            from $(DUCKIEFLEET_ROOT)/scuderia.yaml
    '''
    fn_scuderia = get_scuderia_path()
    try:
        scuderia_contents = read_scuderia(fn_scuderia)
    except ScuderiaException as  e:
        msg = 'Invalid scuderia file %r.' % fn_scuderia
        raise_wrapped(ScuderiaException, e, msg, compact=True)
        
    logger.info('Read %d entries from scuderia %s' % (len(scuderia_contents), fn_scuderia))
    return scuderia_contents

def read_scuderia(scuderia):
    """ Returns the contents of scuderia as a dict, with validated fields."""

    if not os.path.exists(scuderia):
        msg = 'Scuderia file %s does not exist' % scuderia
        raise ScuderiaException(msg)
    
    import yaml

    yaml_string = open(scuderia).read()

    try:
        values = yaml.load(yaml_string)
    except yaml.YAMLError as e:
        msg = 'Yaml file is invalid:\n---\n%s' % e
        raise ScuderiaException(msg)

    if not isinstance(values, dict):
        msg = 'Invalid content: %s' % values
        raise ScuderiaException(msg)

    n = len(values)

    names = ", ".join(sorted(values))
    logger.info('I found %d Duckiebots in the scuderia: %s.' % (n, names))

    results = {}
    
    for k, value in values.items():
        try:
            check_good_name(k)
            
            if not isinstance(value, dict):
                msg = 'Entry should be a dict, found %s' % k
                raise_desc(ScuderiaException, msg)
                
            fields = ['owner_duckietown_id', 'username', 'owner_duckietown_id']
            
            for f in fields:
                if not f in value:
                    msg = 'Could not find field "%s".' % f
                    raise ScuderiaException(msg) 
            
            owner_duckietown_id = value['owner_duckietown_id']
            username = value['username']
            robot_name = k
            
            results[robot_name] = ScuderiaEntry(robot_name=robot_name,  username=username, owner_duckietown_id=owner_duckietown_id)
            
        except ScuderiaException as e:
            msg = 'Invalid entry "%s" in scuderia.' % k
            msg += '\n\n' + indent(yaml.dump(value).strip(), '> ') + '\n    '
            raise_wrapped(ScuderiaException, e, msg, compact=True)

    return results


def check_good_name(name):
    if not name.lower() == name:
        msg = 'Name must be lowercase. %r is not a good name.' % name
        raise ScuderiaException(msg)
