#!/usr/bin/env python3
"""
Test LDAP integration
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)

# ignore rules:
#   docstring
#   too-broad-exception
#   line-too-long
#   too-many-branches
#   too-many-statements
#   too-many-public-methods
#   too-many-lines
#   too-many-nested-blocks
#   toddos (annotations linter handling this)
# pylint: disable=C0111,W0703,C0301,R0912,R0915,R0904,C0302,R1702,W0511

import ldap
import pathlib
import logging


class NSLDAP:
    # handle ldap integration
    group_admin = 'Netboot Admins'

    def __init__(self, server, domain) -> None:
        self.server = f'ldap://{server}'
        self.domain = domain.split('.')[0]
        self.domain_suffix = domain.split('.')[1]
        self.base_dn = f'dc={self.domain},dc={self.domain_suffix}'
        self.client = ldap.initialize(self.server)
        self.client.set_option(ldap.OPT_REFERRALS, 0)  # to search the object and all its descendants
    

    def auth(self, user, password):
        self.client.simple_bind_s(user, password)
        # search_obj = f'userPrincipalName={user}@{self.domain}.{self.domain_suffix}'
        search_obj = 'userPrincipalName=james@rocket.local'
        search_attr = ['memberOf']
        result = self.client.search_s(self.base_dn, ldap.SCOPE_SUBTREE, search_obj, search_attr)
        user_str, res_obj = result[0]
        found_group = False
        if 'memberOf' in res_obj:
            for group in res_obj['memberOf']:
                group_str = group.decode('utf-8')
                g_split = group_str.split(',')
                for entry in g_split:
                    if entry == f'CN={self.group_admin}':
                        logging.info(f'Found membership to group: {self.group_admin}')
                        found_group = True
        if not found_group:
            logging.error(f'failed to authenticate user: {user}')
            return False
        else:
            return True


if __name__ == "__main__":
    CUR_PATH = pathlib.Path(__file__).parent.absolute()
    print('current path: %s' % CUR_PATH)
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = '%(asctime)-15s %(threadName)-10s %(module)-13s:%(lineno)-3d %(funcName)-24s %(levelname)s - %(message)s'
    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)

    try:
        LDAP_SERVER = 'jb-dc0'
        LDAP_DOMAIN = 'rocket.local'
        ldap_conn = NSLDAP(LDAP_SERVER, LDAP_DOMAIN)
        LDAP_USER = 'netboot'
        LDAP_PASSWORD = '882de3c7-65ec'
        if ldap_conn.auth(LDAP_USER, LDAP_PASSWORD):
            logging.info('successfully logged in')
        else:
            logging.error('failed to log in')

    except Exception as e:
        logging.exception('i had an exception')