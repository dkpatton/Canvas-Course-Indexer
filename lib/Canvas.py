""" This module contains classes for the Canvas Data API. """
import os
from time import sleep
import datetime
import requests
import json

class GetData:
    def __init__ (self, end_point, starting_throttle, params=None):
        self.end_point = end_point
        self.params = params
        self.max_attempts = 10
        self.throttle_count = starting_throttle
        # Setup Variables
        setup_folders = ['config', 'data', 'logs']
        for folder in setup_folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
        if not os.path.exists("config/config.json"):
            config = {
                "canvas_address": input("Canvas Address: "),
                "canvas_token": input("Canvas Token: ")
            }
            if config["canvas_address"][-1] == "/":
                config["canvas_address"] = config["canvas_address"][:-1]
            with open("config/config.json", "w", encoding="utf-8") as config_file:
                json.dump(config, config_file, indent=4)
        else:
            with open("config/config.json", "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
            self.canvas_address = config["canvas_address"]
        self.auth = {"Authorization": "Bearer " + config["canvas_token"]}  # authentication header for Canvas API requests
        self.base_url = config["canvas_address"]  # base url for Canvas API requests
        self.backoff_policy = []
        for attempt in range(1, self.max_attempts + 1):
            self.backoff_policy.append(1 * 2 ** (attempt - 1))


    def change_params(self, params):
        """
        Changes the parameters for the request
        """
        self.params = params


    def fetch(self):
        """
        Returns a list of pages of data from a REST API request. Throttling, pagination, 
        and error handling are managed by this function.
        """
        more_pages = False  # flag for whether there are more pages of data to request
        url = self.base_url + self.end_point  # build the url
        params = self.params
        query_list = []  # list of query parameters
        pages = []
        if params is None:
            params = {}
        # Creates url query string like ?param1=value1&param2=value2
        for param in params:
            # if there are multiple values for a parameter, add each one to the query str
            for value in params[param]:  
                # add the parameter and value to the query string 
                query_list.append("{p}={v}".format(p=param, v=str(value)))
        if params != {}:  # if there are query parameters, add them to the url
            url += "?" + "&".join(query_list)  # add the query parameters to the url
        try:  # try to make the request
            request = requests.get(url, headers=self.auth, timeout=60)  # make the request
            print(url)
            print(request.status_code)
            # if the request is throttled, increment the throttle counter.
            # See https://canvas.instructure.com/doc/api/file.throttling.html
            if  float(request.headers["X-Rate-Limit-Remaining"]) < 700.0:
                self.throttle()  # throttle the request
            if "next" not in request.links.keys():  # if there are no more pages of data, return the data
                return request.json()  # return the data
            more_pages = True  # set the flag to True
            pages.extend(request.json()) # add the first page of data to the list of pages
            while more_pages:  # while there are more pages of data, make the request for the next page
                request = requests.get(request.links["next"]["url"], headers=self.auth, timeout=60)  # make the request
                pages.extend(request.json())  # add the page of data to the list of pages
                if  float(request.headers["X-Rate-Limit-Remaining"]) < 700.0:  # if the request is throttled, increment the throttle counter. See https:#canvas.instructure.com/doc/api/file.throttling.html
                    self.throttle()  # throttle the request
                if "next" not in request.links.keys():  # if there are no more pages of data, return the data
                    return pages     
        except requests.exceptions.ConnectionError:  # if there is a connection error, allow to retry
            pass
        return pages

    def throttle(self):  # throttle requests to avoid throttling by Canvas
        """
        Throttles requests to avoid throttling by Canvas. See https:#canvas.instructure.com/doc/api/file.throttling.html
        """
        # if the script has been throttled too many times, quit
        if self.throttle_count == len(self.backoff_policy):  
            quit()
        secs = self.backoff_policy[self.throttle_count]
        self.throttle_count += 1
        sleep(secs)
        return 1


    # Static Methods
    def get_terms(self, n=1):
        """ Returns the canvas term ids based on the last N term codes. """
        previous = {"01": "10", "03": "01", "08": "03", "10": "08"}
        current_year = datetime.datetime.now().year
        year = current_year

        if datetime.datetime.now().month < 4:
            quarter = "01"
        elif datetime.datetime.now().month < 7:
            quarter = "03"
        elif datetime.datetime.now().month < 10:
            quarter = "08"
        else:
            quarter = "10"
        
        term_codes = ["{y}{q}".format(y=year, q=quarter)]
        for i in range(n):
            quarter = previous[quarter]
            if quarter == "10":
                year -= 1
            term_codes.append("{y}{q}".format(y=year, q=quarter))

        # q is a GraphQL query to get the term ID from the term code. See https://canvas.instructure.com/doc/api/graphql.html
        query = """ query TermID {
                        term(sisId: "{sis_id}") {
                            name
                            sisTermId
                            _id
                        }
                    }"""
        enrollment_term_ids = []
        for term_code in term_codes:
            term_req = requests.post(self.base_url + "/api/graphql", # send the query 
                                     headers=self.auth,
                                     params={"query": query.replace("{sis_id}", str(term_code))},
                                     data={},
                                     timeout=60)
            enrollment_term_ids.append(term_req.json()["data"]["term"]["_id"])  # add the term ID to the list of term IDs
        return enrollment_term_ids