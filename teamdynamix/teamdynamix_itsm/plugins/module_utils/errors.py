# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class TeamDynamixError(Exception):
    pass


class AuthError(TeamDynamixError):
    pass


class UnexpectedAPIResponse(TeamDynamixError):
    def __init__(self, status, data):
        self.status = status
        self.data = data
        self.message = "Unexpected response - {0} {1}".format(status, data)
        super(UnexpectedAPIResponse, self).__init__(self.message)
