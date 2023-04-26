# -*- coding: utf-8 -*-
import requests
import datetime
import pandas as pd
from time import sleep

# Setup variables
canvas_address = input("Canvas Address: ")
canvas_token = input("Canvas Token: ")
course_id = input("Course ID: ")
auth = {"Authorization": "Bearer " + canvas_token}  # authentication header for Canvas API requests
GLOBAL_THROTTLE_COUNT = 0  # counter for throttling


# Functions
def rest_request(end_point, params={}):
    """
    Returns a list of pages of data from a REST API request. Throttling, pagination, and error handling are managed by this function.
    """
    more_pages = False  # flag for whether there are more pages of data to request
    url = canvas_address + end_point  # build the url
    query_list = []  # list of query parameters
    pages = []
    for param in params:  # build the query parameters. Creates url query string like ?param1=value1&param2=value2
        for value in params[param]:  # if there are multiple values for a parameter, add each one to the query string
            query_list.append("{p}={v}".format(p=param, v=str(value)))  # add the parameter and value to the query string 
    if params != {}:  # if there are query parameters, add them to the url
        url += "?" + "&".join(query_list)  # add the query parameters to the url
    try:  # try to make the request
        request = requests.get(url, headers=auth, timeout=60)  # make the request
        print(url)
        print(request.status_code)
        if  float(request.headers["X-Rate-Limit-Remaining"]) < 700.0:  # if the request is throttled, increment the throttle counter. See https:#canvas.instructure.com/doc/api/file.throttling.html
            throttle()  # throttle the request
        if "next" not in request.links.keys():  # if there are no more pages of data, return the data
            return request.json()  # return the data
        else:  # if there are more pages of data, set the flag to True
            more_pages = True  # set the flag to True
            pages.extend(request.json()) # add the first page of data to the list of pages
        while more_pages:  # while there are more pages of data, make the request for the next page
            request = requests.get(request.links["next"]["url"], headers=auth, timeout=60)  # make the request
            pages.extend(request.json())  # add the page of data to the list of pages
            if  float(request.headers["X-Rate-Limit-Remaining"]) < 700.0:  # if the request is throttled, increment the throttle counter. See https:#canvas.instructure.com/doc/api/file.throttling.html
                throttle()  # throttle the request
            if "next" not in request.links.keys():  # if there are no more pages of data, return the data
                return pages     
    except requests.exceptions.ConnectionError:  # if there is a connection error, allow to retry
        pass
    # !!! NOTE: This function poorly handles any non-successful HTTP status. !!!


def throttle():  # throttle requests to avoid throttling by Canvas
    """
    Throttles requests to avoid throttling by Canvas. See https:#canvas.instructure.com/doc/api/file.throttling.html
    """
    global GLOBAL_THROTTLE_COUNT
    if GLOBAL_THROTTLE_COUNT == len(backoff_policy):  # if the script has been throttled too many times, pause the script
        log("This is the {n}th time the script has been throttled. The script will now exit.".format(n=GLOBAL_THROTTLE_COUNT), True)
    secs = backoff_policy[GLOBAL_THROTTLE_COUNT]
    GLOBAL_THROTTLE_COUNT += 1
    log("Thread is throttled. Sleeping for {s} seconds.".format(s=secs))  # print the number of seconds the thread.
    sleep(secs)


def exponential_backoff(base, max_attempts):
    """ Makes a sequential list of exponentially growing numbers.

        Args:
        base: The base number of seconds to use for backoff.
        max_attempts: The maximum number of attempts for which to calculate backoff.

        Returns:
        A list of backoff times in seconds.
    """
    backoff_times = []
    for attempt in range(1, max_attempts + 1):
        backoff_times.append(base * 2 ** (attempt - 1))
    return backoff_times


def log(error, panic=False):  # log error and exit
    print("Error: {e}".format(e=error))
    file_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "-{microsec}.log".format(microsec=str(datetime.datetime.now().microsecond))
    with open("logs\\" + file_name, "w") as log:
        if panic:
            log.write(error + "\n\nThe script has encountered an error and will now exit.")
            exit(1)
        else:
            log.write(error)

# Create a backoff policy for throttling. Using (1, 10) as arguments results in 17m3s of total wait time, if throttled again the script will terminate.
backoff_policy = exponential_backoff(1, 10)

# Get all files in course
course_files_endpoint = "/api/v1/courses/:course_id/files"
course_files_url = canvas_address + course_files_endpoint.replace(":course_id", course_id)
course_files = rest_request(course_files_endpoint.replace(":course_id", course_id))
course_files_df = pd.DataFrame(course_files).transpose()
course_files_df.to_json("data/course_files.json", indent=4)

# Get all folders in course
course_folders_endpoint = "/api/v1/courses/:course_id/folders"
course_folders_url = canvas_address + course_folders_endpoint.replace(":course_id", course_id)
course_folders = rest_request(course_folders_endpoint.replace(":course_id", course_id))
course_folders_df = pd.DataFrame(course_folders).transpose()
course_folders_df.to_json("data/course_folders.json", indent=4)

# Get all pages in course
course_pages_endpoint = "/api/v1/courses/:course_id/pages"
course_pages_url = canvas_address + course_pages_endpoint.replace(":course_id", course_id)
course_pages = rest_request(course_pages_endpoint.replace(":course_id", course_id))
course_pages_df = pd.DataFrame(course_pages).transpose()
course_pages_df.to_json("data/course_pages.json", indent=4)

# Get all page content
page_content_endpoint = "/api/v1/courses/:course_id/pages/:url_or_id"
page_content_url = canvas_address + page_content_endpoint.replace(":course_id", course_id)
for page in course_pages:
    page_content = rest_request(page_content_endpoint.replace(":course_id", course_id).replace(":url_or_id", page["url"]))
    page["body"] = page_content["body"]
course_pages_df = pd.DataFrame(course_pages).transpose()
course_pages_df.to_json("data/course_pages.json", indent=4)

page_search_results = {}
for page in course_pages:
    for file in course_files:
        if "files/"+str(file["id"]) in page["body"]:
            page_search_results[str(page["page_id"])+"-"+str(file["id"])] = [page["page_id"], file["id"]]
page_search_results_df = pd.DataFrame.from_dict(page_search_results, orient="index", columns=["page_id", "file_id"])
page_search_results_df.to_json("data/page_search_results.json", indent=4)
