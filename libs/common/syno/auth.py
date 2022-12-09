import requests


class Authentication:
    def __init__(self, ip_address, port, username, password):
        self._ip_address = ip_address
        self._port = port
        self._username = username
        self._password = password
        self._sid = None
        self._session_expire = True
        self._base_url = 'http://%s:%s/webapi/' % (self._ip_address, self._port)

        self.full_api_list = {}

    def login(self, application):
        self.get_api_list('SYNO.API.Auth')
        login_api = 'auth.cgi?api=SYNO.API.Auth'
        param = {'version': self.full_api_list['SYNO.API.Auth']['maxVersion'], 'method': 'login', 'account': self._username,
                 'passwd': self._password, 'session': application, 'format': 'cookie'}

        if not self._session_expire:
            if self._sid is not None:
                self._session_expire = False
                return 'User already logged'
        else:
            session_request = requests.get(self._base_url + login_api, param)
            self._sid = session_request.json()['data']['sid']
            self._session_expire = False
            return 'User logging... New session started!'

    def logout(self, application):
        logout_api = 'auth.cgi?api=SYNO.API.Auth'
        param = {'version': self.full_api_list['SYNO.API.Auth']['maxVersion'], 'method': 'logout', 'session': application}

        response = requests.get(self._base_url + logout_api, param)
        if response.json()['success'] is True:
            self._session_expire = True
            self._sid = None
            return 'Logged out'
        else:
            self._session_expire = True
            self._sid = None
            return 'No valid session is open'

    def get_api_list(self, app=None):
        query_path = 'query.cgi?api=SYNO.API.Info'
        list_query = {'version': '1', 'method': 'query', 'query': 'all'}

        response = requests.get(self._base_url + query_path, list_query).json()

        if app is not None:
            for key in response['data']:
                if app.lower() in key.lower():
                    self.full_api_list[key] = response['data'][key]
        else:
            self.full_api_list = response['data']

        return

    def show_api_name_list(self):
        prev_key = ''
        for key in self.full_api_list:
            if key != prev_key:
                print(key)
                prev_key = key
        return

    def show_json_response_type(self):
        for key in self.full_api_list:
            for sub_key in self.full_api_list[key]:
                if sub_key == 'requestFormat':
                    if self.full_api_list[key]['requestFormat'] == 'JSON':
                        print(key + '   Returns JSON data')
        return

    def search_by_app(self, app):
        print_check = 0
        for key in self.full_api_list:
            if app.lower() in key.lower():
                print(key)
                print_check += 1
                continue
        if print_check == 0:
            print('Not Found')
        return

    def request_data(self, api_name, api_path, req_param, method=None, response_json=True):  # 'post' or 'get'

        # Convert all booleen in string in lowercase because Synology API is waiting for "true" or "false"
        for k,v in req_param.items():
            if isinstance(v, bool):
                req_param[k] = str(v).lower()

        if method is None:
            method = 'get'

        req_param['_sid'] = self._sid

        if method == 'get':
            url = ('%s%s' % (self._base_url, api_path)) + '?api=' + api_name
            response = requests.get(url, req_param)

            if response_json is True:
                return response.json()
            else:
                return response

        elif method == 'post':
            url = ('%s%s' % (self._base_url, api_path)) + '?api=' + api_name
            response = requests.post(url, req_param)

            if response_json is True:
                return response.json()
            else:
                return response

    @property
    def sid(self):
        return self._sid

    @property
    def base_url(self):
        return self._base_url
