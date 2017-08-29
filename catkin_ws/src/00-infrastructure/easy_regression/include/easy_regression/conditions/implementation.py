from duckietown_utils.exceptions import DTConfigException
from easy_regression.conditions.references import parse_reference
from easy_regression.conditions.binary import parse_binary
from easy_regression.conditions.eval import BinaryEval, Wrapper

def _parse_regression_test_check(line):
    line = line.strip()
    tokens = line.split(' ')
    if len(tokens) != 3:
        msg = 'I expect exactly 3 tokens.\nLine: "%s"\nTokens: %s' % (line, tokens)
        raise DTConfigException(msg)
    
    ref1 = parse_reference(tokens[0])
    binary = parse_binary(tokens[1])
    ref2 = parse_reference(tokens[2])
    evaluable = BinaryEval(ref1, binary, ref2)
    return Wrapper(evaluable)
