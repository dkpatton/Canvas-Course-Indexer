# -*- coding: utf-8 -*-
""" Extracts files, pages, assignments and folders from all coureses in a term.
    All the data is saved as a json file to converted into a search index usable 
    in PowerBI or PowerQuery for Excel.
"""

import json
from genson import SchemaBuilder
from lib.Canvas import GetData as gcd

def handler (end_point, params):
    global THROTTLE_COUNTER
    data = gcd(end_point, THROTTLE_COUNTER, params)
    response = data.fetch()
    THROTTLE_COUNTER += data.throttle_count
    return response

global THROTTLE_COUNTER # Throttle counter
THROTTLE_COUNTER = 0

ROOT_ACCT = 1 # Root account ID (probably 1)
MAIN_SUBACCT = 2  # Main subaccount ID, where children are sub-accounts
SUBACCT_IDS = "1,2,3"  # Sub-account IDs to search
TOPN = 1  # Number of terms to search
COURSE_NAME_FILTER_EXCLUDE = None  # Exclude courses with the name filter in the name

# List active courses in an account
courses = []
EPSTR = "/api/v1/accounts/{main_account}/courses".format(main_account=MAIN_SUBACCT)
courses_unhandled = gcd(EPSTR, THROTTLE_COUNTER)  # Not using hanlder to reuse the same object
for term in courses_unhandled.get_terms(TOPN):
    params = {"enrollment_type[]": ["student"],"with_enrollments": [True],"published": [True],
              "by_subaccounts": ["{subaccount_ids}".format(subaccount_ids=SUBACCT_IDS)],
              "enrollment_term_id": [term]}
    courses_unhandled.change_params(params)
    for course in courses_unhandled.fetch():
        if COURSE_NAME_FILTER_EXCLUDE == None:
            courses.append(course)
        elif course["name"].find(COURSE_NAME_FILTER_EXCLUDE) == -1:
            courses.append(course)

index = {}
for course in courses:
    # Get a list of all pages and store in index
    course_id = course["id"]
    index[course_id] = {}
    EPSTR = "/api/v1/courses/{course_id}/pages"
    pages = handler(EPSTR.format(course_id=course_id), {"sort": ["updated_at"], "order": ["desc"]})
    index[course_id]["pages"] = {}
    for page in pages:
        page_id = page["page_id"]
        index[course_id]["pages"][page_id] = page

    # Get all page contents and store in index
    for page in pages:
        EPSTR="/api/v1/courses/{course_id}/pages/{id}"
        page_id = page["page_id"]
        content = handler(EPSTR.format(course_id=course_id, id=page_id), None)
        index[course_id]["pages"][page_id]["content"] = content
    

    # Get course-level student summary data
    EPSTR = "/api/v1/courses/{course_id}/analytics/student_summaries"
    student_summaries = handler(EPSTR.format(course_id=course_id), {"sort_column": ["page_views_descending"]})

    # Get all assignments and store in index
    EPSTR = "/api/v1/courses/{course_id}/assignments"
    assignments = handler(EPSTR.format(course_id=course_id), None)
    index[course_id]["assignments"] = assignments

    # Get all modules and store in index
    EPSTR = "/api/v1/courses/{course_id}/modules"
    modules = handler(EPSTR.format(course_id=course_id), None)
    index[course_id]["modules"] = modules

    # Get all files and store in index
    EPSTR = "/api/v1/courses/{course_id}/files"
    files = handler(EPSTR.format(course_id=course_id), None)
    index[course_id]["files"] = files
    PAGES_SEARCH_STR = "files/{file_id}"
    for file in index[course_id]["files"]:
        file["linked_page_id"] = []
        text_to_find = PAGES_SEARCH_STR.format(file_id=file["id"])
        for page in index[course_id]["pages"]:
            page_id = page
            if index[course_id]["pages"][page]["content"]["body"].find(text_to_find) != -1:
                file["linked_page_id"].append(page_id)
    
    # Export course to json file
    file_name = "data/{course_id}-{prefix}.json"
    with open(file_name.format(course_id=course_id, prefix="data"), "w") as f:
        json.dump(index, f, indent=4)

    # Make schema
    builder = SchemaBuilder()
    with open(file_name.format(course_id=course_id, prefix="data"), "r") as f:
        datastore = json.load(f)
        builder.add_object(datastore)
    schema = builder.to_schema()
    
    with open(file_name.format(course_id=course_id, prefix="schema"), "w") as f:
        json.dump(schema, f, indent=4)
