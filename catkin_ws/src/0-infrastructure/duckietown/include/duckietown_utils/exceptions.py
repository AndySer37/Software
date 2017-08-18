
class DTUserError(Exception):
    """ Exceptions that will not be printed with full traceback,
        because they contain a simple message for the user, to be printed in red.
    """

class DTConfigException(DTUserError):
    pass

import sys
import traceback

from duckietown_utils import logger


def wrap_script_entry_point(function,
                            exceptions_no_traceback=(DTUserError,)):
    """
        Wraps the main() of a script.
        For Exception: we exit with value 2.
        
        :param exceptions_no_traceback: tuple of exceptions for which we 
         just print the error, and exit with value 1.
        
    """
    try:
        ret = function()
        if ret is None:
            ret = 0
        sys.exit(ret)
    except exceptions_no_traceback as e:
        s = "Error during execution of %s:" % function.__name__
        s += '\n' + str(e)
        logger.error(s)
        sys.exit(1)
    except Exception as e:
        logger.error(traceback.format_exc(e))
        sys.exit(2)
