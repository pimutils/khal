#!/usr/bin/env python
# this script should generate a rst file describing khal's configuration for
# inclusion in khal's sphinx based documentation.
from __future__ import print_function
from configobj import ConfigObj
import validate

specpath = '../../khal/settings/khal.spec'
config = ConfigObj(None, configspec=specpath, stringify=False, list_values=False)
validator = validate.Validator()
config.validate(validator)
spec = config.configspec


def write_section(specsection, secname, key, comment):
    # why is _parse_check a "private" method? seems to be rather useful...
    # we don't need fun_kwargs
    fun_name, fun_args, fun_kwargs, default = validator._parse_check(specsection)
    print('\n.. _{}-{}:'.format(secname, key))
    print('\n.. object:: {}\n'.format(key))
    print('    ' + '\n    '.join([line.strip('# ') for line in comment]))
    if fun_name == 'option':
        fun_args = ['*{}*'.format(arg) for arg in fun_args]
        fun_args = fun_args[:-2] + [fun_args[-2] + ' and ' + fun_args[-1]]
        fun_name += ', allowed values are {}'.format(', '.join(fun_args))
        fun_args = []
    if fun_name == 'integer' and len(fun_args) == 2:
        fun_name += ', allowed values are between {} and {}'.format(
            fun_args[0], fun_args[1])
        fun_args = []
    print()
    if fun_name in ['expand_db_path', 'expand_path']:
        fun_name = 'string'
    elif fun_name in ['force_list']:
        fun_name = 'list'
        if isinstance(default, list):
            default = ['space' if one == ' ' else one for one in default]
            default = ', '.join(default)

    print('      :type: {}'.format(fun_name))
    if fun_args != []:
        print('      :args: {}'.format(fun_args))
    print('      :default: {}'.format(default))


for secname in spec:
    print()
    heading = 'The [{}] section'.format(secname)
    print('{}\n{}'.format(heading, len(heading) * '~'))
    comment = spec.comments[secname]
    print('\n'.join([line[2:] for line in comment]))

    for key, comment in spec[secname].comments.items():
        if key == '__many__':
            comment = spec[secname].comments[key]
            print('\n'.join([line[2:] for line in comment]))
            for key, comment in spec[secname]['__many__'].comments.items():
                write_section(spec[secname]['__many__'][key], secname,
                              key, comment)
        else:
            write_section(spec[secname][key], secname, key, comment)
