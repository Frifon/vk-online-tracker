# -*- coding: utf8 -*-

__author__ = 'vient'

from app.common.tools import vk_api_authorization
from vk_api.vk_api import ApiError

from collections import deque
import traceback
import sys


class Add_request:
    execute_limit = 25
    login_refresh_limit = 10000
    login_refresh_counter = login_refresh_limit
    requests = deque()
    callbacks = deque()
    _execute_mutex = False  # Preventing stack overflow, also preserving the order of callbacks and responces
    vk_api = None
    force_index = -1        # Index of last request to be force execute

    # add_photo_request() variables
    photo_limit = 100    # how much photos to get in 1 request
    photo_values_in_process = deque()
    photo_values = deque()
    photo_callbacks = deque()


    def photos_callback(responce):
        self = Add_request 
        popped = 0

        if responce is False:
            for i in range(self.photo_limit):
                self.photo_values_in_process.popleft()
                self.photo_callbacks.popleft()(False)
            return

        for photo_info in responce:
            processed = False

            while len(self.photo_values_in_process) > 0 and not processed:
                photo_id = self.photo_values_in_process.popleft().split('_')[1]
                if photo_id != str(photo_info['id']):
                    self.photo_callbacks.popleft()(False)
                else:
                    self.photo_callbacks.popleft()(photo_info)
                    processed = True
                popped += 1

                if __debug__ and len(self.photo_values_in_process) > 0:
                    print(self.photo_values_in_process[0], end=' ')

            if len(self.photo_values_in_process) == 0 and not processed:
                print('FATAL ERROR IN news.common.api_requests.Add_request.photos_callback')
                print('REQUEST FOR PHOTO IS MISSING')
                exit(-1)

        while popped < self.photo_limit:
            self.photo_values_in_process.popleft()
            self.photo_callbacks.popleft()(False)
            popped += 1

    def execute_requests(self):
        if self._execute_mutex is True:
            return

        self._execute_mutex = True

        if self.login_refresh_counter == self.login_refresh_limit:
            self.login_refresh_counter = 0
            while True:
                try:
                    if __debug__:
                        print('trying to connect...', end=' ')
                    self.vk_api = vk_api_authorization()
                    break
                    '''
                    if vk_api is None:
                        print('Something went wrong. Maybe wrong credentials?')
                        exit(0)
                    '''
                except KeyboardInterrupt:
                    traceback.print_exc()
                    exit(0)
                except:
                    print("Unexpected error:", sys.exc_info()[0])
                    pass
            if __debug__:
                print('success!')
        self.login_refresh_counter += 1

        while len(self.requests) >= self.execute_limit or self.force_index >= 0:
            if __debug__:
                print('execute started...')

            execute_limit_backup = self.execute_limit
            if self.force_index >= 0:
                # safe because _execute_mutex is locked
                self.execute_limit = min(self.execute_limit, len(self.requests))

            current_requests = 0
            request = 'return ['

            while len(self.requests) > 0 and current_requests < self.execute_limit:
                now = self.requests.popleft()
                if __debug__:
                    print('Added request ', now[0], ', values ', now[1])
                request += 'API.{req[0]}({req[1]}), '.format(req=now)
                current_requests += 1
            request = (request[:-2] + '];').replace("'", '"')

            while True:
                try:
                    resp = self.vk_api.method("execute", {"code": request})
                    break
                except KeyboardInterrupt:
                    traceback.print_exc()
                    exit(0)
                except ApiError:
                    print('Too many requests per second. Trying again.')
                except:
                    if __debug__:
                        traceback.print_exc()
                    pass

            index = 0
            while current_requests > 0:
                if __debug__:
                    print('.', end=' ')
                self.callbacks.popleft()(resp[index])
                index += 1
                current_requests -= 1

            self.force_index = max(self.force_index - self.execute_limit, -1)
            self.execute_limit = execute_limit_backup

            if __debug__:
                print('\n---------------')    # DEBUG PRINT

        self._execute_mutex = False

    def add_photo_request(self, values, callback):
        self.photo_values.append(values['photos'])
        self.photo_callbacks.append(callback)
        print("Length of photos to be processed ", len(self.photo_values))
        if __debug__:
            print('add_photo_request', values['photos'], len(self.photo_values), len(self.photo_values_in_process), len(self.photo_callbacks))
        if len(self.photo_values) >= self.photo_limit:
            final_request = []
            for i in range(self.photo_limit):
                req = self.photo_values.popleft()
                final_request.append(req)
                self.photo_values_in_process.append(req)

            final_request = ','.join(final_request)
            final_values = {
                'photos': final_request,
                'extended': 1
            }
            self.requests.append(['photos.getById', str(final_values)])
            self.callbacks.append(self.photos_callback)

            self.execute_requests(self)

    def execute_now(self):
        self.force_index = len(self.requests) - 1
        self.execute_requests()

    def __init__(self, method, values, callback):
        self = Add_request

        if (method == 'photos.getByIdOptimized'):
            self.add_photo_request(self, values, callback)
            return

        self.requests.append([method, str(values)])
        self.callbacks.append(callback)
        
        self.execute_requests(self)
